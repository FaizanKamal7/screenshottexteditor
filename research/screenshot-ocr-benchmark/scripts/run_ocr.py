"""Run OCR engines over the pilot manifest (host-side orchestrator, stdlib only).

Each engine runs in its own long-lived worker process (scripts/engines/worker.py):
Linux engines inside their Docker image with --network none, windows_ocr in a
local venv on the Windows host. The orchestrator never decodes images; it only
checks that every worker saw the exact file bytes and decoded pixels recorded
in the manifest (PILOT_PLAN E5/E6).

Passes:
  accuracy     all OCR'd images, engines in parallel (timings are contended and
               are NOT runtime results). Resumable.
  serial-check re-run, one engine at a time, any image whose contended call took
               > 120 s, so the 120 s timeout rule (PREREGISTRATION §3) is applied
               to uncontended time only.
  rerun        determinism subset (10%, seeded) -> predictions_rerun/ (E3)
  timing       V00 images, 3 reps, interleaved rep -> image -> engine, serial (M10/F2)

    python scripts/run_ocr.py accuracy --engines all
"""

import argparse
import datetime as dt
import json
import os
import platform
import queue
import random
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT = os.path.join(ROOT, "pilot")
DATASET = os.path.join(PILOT, "dataset")
# Hang guard only (PREREGISTRATION §3, amendment A3b): output that completes is scored
# however long it took; speed is reported separately (M10). Was 120 s as a failure rule;
# paddle_v5_server needs ~140-240 s for 2560x1600 on the reference CPU.
TIMEOUT_S = 900.0
WATCHDOG_S = 900.0
SEED = 20260924
# Declared reference-host memory budget for each Linux engine container
# (PREREGISTRATION §8.3 amendment A3). Swap is disabled so exceeding it is an
# unambiguous cgroup OOM kill, which Docker reports as State.OOMKilled.
MEMORY_LIMIT = "24g"

ENGINES = {
    "tesseract5": "ocrbench-ocr-tesseract:pilot",
    "paddle_v5_mobile": "ocrbench-ocr-paddle:pilot",
    "paddle_v5_server": "ocrbench-ocr-paddle:pilot",
    "easyocr": "ocrbench-ocr-torch:pilot",
    "doctr": "ocrbench-ocr-torch:pilot",
    "windows_ocr": None,  # native Windows host
}
WINDOWS_PYTHON = os.path.join(ROOT, ".venv-winocr", "Scripts", "python.exe")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_manifest() -> list[dict]:
    with open(os.path.join(DATASET, "manifest.jsonl"), encoding="utf-8") as f:
        return [json.loads(line) for line in f]


class Worker:
    def __init__(self, engine_id: str):
        self.engine_id = engine_id
        self.proc = None
        self.q: queue.Queue = queue.Queue()
        self.name = None
        self.init_s = None
        self.starts = 0

    def _cmd(self) -> list[str]:
        image = ENGINES[self.engine_id]
        if image is None:
            return [WINDOWS_PYTHON, os.path.join(ROOT, "scripts", "engines", "worker.py"), "--engine", self.engine_id]
        self.name = f"ocrb-{self.engine_id}-{os.getpid()}-{self.starts}"
        # No --rm: after a worker dies, container_state() reads OOMKilled before removal.
        return ["docker", "run", "-i", "--name", self.name, "--network", "none",
                "--memory", MEMORY_LIMIT, "--memory-swap", MEMORY_LIMIT,
                "-v", f"{ROOT}:/bench:ro", "-w", "/bench/scripts/engines", image,
                "python", "worker.py", "--engine", self.engine_id]

    def container_state(self) -> dict | None:
        """Docker's record of why the container stopped (None for the Windows worker)."""
        if not self.name:
            return None
        out = subprocess.run(["docker", "inspect", self.name, "--format",
                              "{{.State.OOMKilled}} {{.State.ExitCode}} {{.State.Status}}"],
                             capture_output=True, text=True)
        parts = out.stdout.split()
        if len(parts) != 3:
            return {"inspect_error": out.stderr.strip()[:200]}
        return {"oom_killed": parts[0] == "true", "exit_code": int(parts[1]), "status": parts[2]}

    def path(self, rel: str) -> str:
        if ENGINES[self.engine_id] is None:
            return os.path.join(DATASET, rel)
        return "/bench/pilot/dataset/" + rel

    def start(self) -> None:
        self.starts += 1
        self.q = queue.Queue()
        log = open(os.path.join(PILOT, "logs", f"{self.engine_id}.stderr.log"), "a", encoding="utf-8")
        log.write(f"\n==== start {now()} ====\n")
        log.flush()
        self.proc = subprocess.Popen(self._cmd(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                     text=True, encoding="utf-8", bufsize=1)
        threading.Thread(target=self._reader, args=(self.proc, self.q), daemon=True).start()
        ready = self.q.get(timeout=1800)
        if ready is None or not ready.get("ready"):
            raise RuntimeError(f"{self.engine_id} failed to start: {ready}")
        self.init_s = ready["init_s"]

    @staticmethod
    def _reader(proc, q) -> None:
        for line in proc.stdout:
            line = line.strip()
            if line:
                try:
                    q.put(json.loads(line))
                except json.JSONDecodeError:
                    q.put({"ok": False, "error": f"non-JSON worker output: {line[:200]}"})
        q.put(None)

    def request(self, obj: dict, timeout: float):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return "timeout"

    def kill(self) -> None:
        if self.name:
            subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        self.proc = None

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                self.request({"cmd": "quit"}, timeout=30)
            except (BrokenPipeError, OSError):
                pass
        self.kill()

    def run_image(self, row: dict, watchdog: float) -> dict:
        """One image; on crash, restart once and retry; on watchdog, kill + restart.

        A worker death is classified from Docker's own record: OOMKilled -> status
        "resource_oom" (exceeded the declared memory budget; PREREGISTRATION
        amendment A3), anything else -> "error" (engine failure, scored empty)."""
        states = []
        for attempt in (1, 2):
            if self.proc is None or self.proc.poll() is not None:
                self.start()
            t0 = time.perf_counter()
            resp = self.request({"cmd": "run", "path": self.path(row["file"])}, timeout=watchdog)
            wall = time.perf_counter() - t0
            if resp == "timeout":
                self.kill()
                return {"status": "timeout", "error": f"no response within {watchdog:.0f} s", "wall_s": wall,
                        "attempts": attempt}
            if resp is None:  # worker died mid-request
                if self.proc is not None:
                    try:
                        self.proc.wait(timeout=60)
                    except subprocess.TimeoutExpired:
                        pass
                states.append(self.container_state())
                self.kill()
                if attempt == 1:
                    continue
                oom = all(s and s.get("oom_killed") for s in states)
                return {"status": "resource_oom" if oom else "error",
                        "error": ("container OOM-killed at the declared memory limit (twice)" if oom
                                  else "worker process died (twice)"),
                        "container_states": states, "wall_s": wall, "attempts": attempt}
            resp["wall_s"] = wall
            resp["attempts"] = attempt
            resp["status"] = "ok" if resp.get("ok") else "error"
            return resp
        raise AssertionError("unreachable")


def prediction_record(worker: Worker, info: dict, row: dict, resp: dict, run_pass: str, conditions: str) -> dict:
    return {
        "engine_id": worker.engine_id,
        "engine_version": info.get("engine_version"),
        "config": info.get("config"),
        "image_id": row["image_id"],
        "status": resp["status"],
        "error": resp.get("error"),
        "total_s": resp.get("total_s"),
        "detect_s": resp.get("detect_s"),
        "recognize_s": resp.get("recognize_s"),
        "orchestrator_wall_s": resp.get("wall_s"),
        "attempts": resp.get("attempts"),
        "input_file_sha256_ok": resp.get("file_sha256") == row["sha256"] if resp["status"] == "ok" else None,
        "input_pixel_sha256_ok": resp.get("pixel_sha256") == row["pixel_sha256"] if resp["status"] == "ok" else None,
        "input_pixel_sha256": resp.get("pixel_sha256"),
        "peak_rss_mb": resp.get("peak_rss_mb"),
        "peak_rss_scope": resp.get("peak_rss_scope"),
        "container_states": resp.get("container_states"),
        "memory_limit": MEMORY_LIMIT if ENGINES[worker.engine_id] else None,
        "lines": resp.get("lines", []),
        "pass": run_pass,
        "conditions": conditions,
        "completed_at": now(),
    }


def get_info(worker: Worker) -> dict:
    if worker.proc is None:
        worker.start()
    resp = worker.request({"cmd": "info"}, timeout=300)
    info = resp.get("info", {}) if isinstance(resp, dict) else {}
    info["init_s"] = worker.init_s
    image = ENGINES[worker.engine_id]
    if image:
        out = subprocess.run(["docker", "image", "inspect", image, "--format", "{{.Id}}"], capture_output=True,
                             text=True)
        info["docker_image"] = image
        info["docker_image_id"] = out.stdout.strip()
    else:
        info["host_python"] = sys.version
    return info


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def accuracy_engine(engine_id: str, rows: list[dict], out_dir: str, run_pass: str, conditions: str,
                    watchdog: float) -> None:
    worker = Worker(engine_id)
    info = get_info(worker)
    write_json(os.path.join(PILOT, "engines", f"{engine_id}.info.json"), info)
    done = 0
    for row in rows:
        path = os.path.join(out_dir, engine_id, f"{row['image_id']}.json")
        if os.path.exists(path):
            continue
        resp = worker.run_image(row, watchdog)
        write_json(path, prediction_record(worker, info, row, resp, run_pass, conditions))
        done += 1
        if done % 25 == 0:
            print(f"[{now()}] {engine_id}: {done} new predictions", flush=True)
    worker.stop()
    print(f"[{now()}] {engine_id}: finished ({done} new)", flush=True)


def cmd_accuracy(engines: list[str]) -> None:
    rows = [r for r in load_manifest() if r["ocr"]]
    out = os.path.join(PILOT, "predictions")
    conditions = "parallel" if len(engines) > 1 else "single-engine"
    threads = [threading.Thread(target=accuracy_engine, args=(e, rows, out, "accuracy", conditions, WATCHDOG_S))
               for e in engines]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def cmd_serial_check(engines: list[str]) -> None:
    """Re-run, uncontended, every image that hit the hang guard (or took longer than it)."""
    rows = {r["image_id"]: r for r in load_manifest() if r["ocr"]}
    log = []
    for engine_id in engines:
        pred_dir = os.path.join(PILOT, "predictions", engine_id)
        slow = []
        for name in sorted(os.listdir(pred_dir)):
            with open(os.path.join(pred_dir, name), encoding="utf-8") as f:
                p = json.load(f)
            wall = p.get("orchestrator_wall_s") or 0
            if p["status"] == "timeout" or wall > TIMEOUT_S:
                slow.append(p["image_id"])
        if not slow:
            continue
        worker = Worker(engine_id)
        info = get_info(worker)
        for image_id in slow:
            row = rows[image_id]
            resp = worker.run_image(row, TIMEOUT_S)
            rec = prediction_record(worker, info, row, resp, "serial-check", "serial")
            write_json(os.path.join(PILOT, "predictions", engine_id, f"{image_id}.json"), rec)
            log.append({"engine_id": engine_id, "image_id": image_id, "status": rec["status"],
                        "wall_s": resp.get("wall_s")})
        worker.stop()
    write_json(os.path.join(PILOT, "logs", "serial_check.json"), log)
    print(f"serial-check: {len(log)} re-runs")


def determinism_subset(rows: list[dict]) -> list[dict]:
    rng = random.Random(SEED)
    k = max(1, round(0.10 * len(rows)))
    return sorted(rng.sample(rows, k), key=lambda r: r["image_id"])


def cmd_rerun(engines: list[str]) -> None:
    rows = determinism_subset([r for r in load_manifest() if r["ocr"]])
    out = os.path.join(PILOT, "predictions_rerun")
    conditions = "parallel" if len(engines) > 1 else "single-engine"
    threads = [threading.Thread(target=accuracy_engine, args=(e, rows, out, "rerun", conditions, WATCHDOG_S))
               for e in engines]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def cmd_timing(engines: list[str], reps: int) -> None:
    rows = [r for r in load_manifest() if r["variant"] == "V00"]
    workers = {e: Worker(e) for e in engines}
    infos = {e: get_info(w) for e, w in workers.items()}
    out_path = os.path.join(PILOT, "timing", "timing.jsonl")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # Untimed warm-up per engine (METHODOLOGY M10).
    for e, w in workers.items():
        w.run_image(rows[0], WATCHDOG_S)
    with open(out_path, "w", encoding="utf-8") as f:
        for rep in range(reps):
            for row in rows:
                for e, w in workers.items():
                    resp = w.run_image(row, WATCHDOG_S)
                    f.write(json.dumps({"rep": rep, "image_id": row["image_id"], "engine_id": e,
                                        "status": resp["status"], "total_s": resp.get("total_s"),
                                        "orchestrator_wall_s": resp.get("wall_s"), "width": row["width"],
                                        "height": row["height"], "form_factor": row["form_factor"],
                                        "at": now()}) + "\n")
                    f.flush()
            print(f"[{now()}] timing rep {rep} done", flush=True)
    for w in workers.values():
        w.stop()
    write_json(os.path.join(PILOT, "timing", "engines_at_timing.json"), infos)


def cmd_environment() -> None:
    def run(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout.strip()
        except Exception as exc:  # recorded, not fatal
            return f"error: {exc!r}"

    env = {
        "recorded_at": now(),
        "host": {
            "platform": platform.platform(),
            "processor": run(["powershell", "-NoProfile", "-Command",
                              "(Get-CimInstance Win32_Processor | Select-Object -First 1 Name,NumberOfCores,"
                              "NumberOfLogicalProcessors | ConvertTo-Json)"]),
            "ram_bytes": run(["powershell", "-NoProfile", "-Command",
                              "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"]),
            "python": sys.version,
        },
        "docker_version": run(["docker", "version", "--format", "{{json .}}"]),
        "docker_info": run(["docker", "info", "--format", "{{json .}}"]),
        "git_head": run(["git", "-C", ROOT, "rev-parse", "HEAD"]),
        "git_status_research": run(["git", "-C", ROOT, "status", "--porcelain", "--", "."]),
        "images": {},
    }
    for image in sorted({i for i in ENGINES.values() if i} | {"ocrbench-tools:pilot"}):
        env["images"][image] = {
            "id": run(["docker", "image", "inspect", image, "--format", "{{.Id}}"]),
            "pip_freeze": run(["docker", "run", "--rm", "--network", "none", image, "pip", "freeze"]).splitlines(),
        }
    env["windows_ocr_venv_pip_freeze"] = run([WINDOWS_PYTHON, "-m", "pip", "freeze"]).splitlines()
    write_json(os.path.join(PILOT, "environment", "environment.json"), env)
    print("environment recorded")


def cmd_lock() -> None:
    """engines.lock.json from each engine's recorded worker info (PILOT E4)."""
    engines = {}
    for e in ENGINES:
        path = os.path.join(PILOT, "engines", f"{e}.info.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                engines[e] = json.load(f)
    write_json(os.path.join(PILOT, "engines.lock.json"), {
        "status": "PILOT lock — provisional (PREREGISTRATION D1 unresolved for Paddle)",
        "recorded_at": now(), "engines": engines,
    })
    print(f"lock written for {sorted(engines)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["accuracy", "serial-check", "rerun", "timing", "environment", "lock"])
    parser.add_argument("--engines", nargs="*", default=["all"])
    parser.add_argument("--reps", type=int, default=3)
    args = parser.parse_args()
    engines = list(ENGINES) if args.engines == ["all"] else args.engines
    os.makedirs(os.path.join(PILOT, "logs"), exist_ok=True)
    t0 = time.perf_counter()
    started = now()
    if args.cmd == "accuracy":
        cmd_accuracy(engines)
    elif args.cmd == "serial-check":
        cmd_serial_check(engines)
    elif args.cmd == "rerun":
        cmd_rerun(engines)
    elif args.cmd == "timing":
        cmd_timing(engines, args.reps)
    elif args.cmd == "environment":
        cmd_environment()
    elif args.cmd == "lock":
        cmd_lock()
    elapsed = time.perf_counter() - t0
    with open(os.path.join(PILOT, "logs", "passes.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"cmd": args.cmd, "engines": engines, "started": started, "finished": now(),
                            "elapsed_s": round(elapsed, 3)}) + "\n")
    print(f"{args.cmd} elapsed_s={elapsed:.1f}")


if __name__ == "__main__":
    main()
