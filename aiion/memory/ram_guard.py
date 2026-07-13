"""aiion/memory/ram_guard.py — Monitor de presión de RAM con swap automático."""
import os, threading, time, gc, subprocess, shutil
from pathlib import Path
from collections import deque
from aiion.cli.ui import c, CO, GR, YL, RE, BOLD

class RamGuard:
    STATES     = ["VERDE","AMARILLO","ROJO","CRÍTICO"]
    THRESHOLDS = [0.60, 0.80, 0.90, 1.0]
    INTERVAL   = 20
    SWAP_FILE  = str(Path.home() / "swapfile")
    SWAP_MB    = 1024

    def __init__(self):
        self._stop        = threading.Event()
        self._thread      = None
        self._state       = "VERDE"
        self._history     = deque(maxlen=20)
        self._actions     = 0
        self._swap_active = False

    def start(self):
        self._thread = threading.Thread(target=self._loop, name="RamGuard", daemon=True)
        self._thread.start()

    def stop(self): self._stop.set()

    def _meminfo(self):
        info = {}
        try:
            for line in Path("/proc/meminfo").read_text().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip()] = int(v.strip().split()[0])
        except: pass
        return info

    def pressure(self):
        m = self._meminfo()
        return 1.0 - (m.get("MemAvailable", m.get("MemTotal",1)) / max(m.get("MemTotal",1),1))

    def stats_str(self):
        m       = self._meminfo()
        total   = m.get("MemTotal",0)//1024
        avail   = m.get("MemAvailable",0)//1024
        used    = total - avail
        pct     = self.pressure()*100
        col     = GR if pct<60 else YL if pct<80 else RE
        return f"{c(CO,'RAM')} {c(col+BOLD,f'{pct:.0f}%')} {c(CO,f'{used}/{total}MB')}"

    def trend(self):
        if len(self._history)<4: return "estable"
        ts=[x[0] for x in self._history]; ps=[x[1] for x in self._history]
        n=len(ts); t0=ts[0]; ts2=[t-t0 for t in ts]
        mt=sum(ts2)/n; mp=sum(ps)/n
        num=sum((ts2[i]-mt)*(ps[i]-mp) for i in range(n))
        den=sum((ts2[i]-mt)**2 for i in range(n)) or 1
        spm=(num/den)*60
        if abs(spm)<0.005: return "estable"
        return f"↑{spm:.1%}/m" if spm>0 else f"↓{abs(spm):.1%}/m"

    def _classify(self,p):
        for thresh,state in zip(self.THRESHOLDS,self.STATES):
            if p<thresh: return state
        return "CRÍTICO"

    def _loop(self):
        time.sleep(4)
        while not self._stop.is_set():
            try:
                p=self.pressure(); self._history.append((time.time(),p))
                self._state=self._classify(p)
                if p>=0.60: gc.collect()
                if p>=0.80: self._ensure_swap()
                if p>=0.90: self._kill_zombies()
            except: pass
            self._stop.wait(self.INTERVAL)

    def _ensure_swap(self):
        if self._swap_active: return
        try:
            if self._meminfo().get("SwapTotal",0)>0:
                self._swap_active=True; return
            free=shutil.disk_usage(str(Path.home())).free//(1024*1024)
            if free<self.SWAP_MB+200: return
            sp=Path(self.SWAP_FILE)
            if not sp.exists():
                subprocess.run(f"dd if=/dev/zero of={self.SWAP_FILE} bs=1M count={self.SWAP_MB} 2>/dev/null",
                               shell=True,timeout=90)
                subprocess.run(f"chmod 600 {self.SWAP_FILE} && mkswap {self.SWAP_FILE}",
                               shell=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            subprocess.run(f"swapon {self.SWAP_FILE}",shell=True,
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self._swap_active=True; self._actions+=1
        except: pass

    def _kill_zombies(self):
        try:
            r=subprocess.run("ps aux|grep '[n]ode'|awk '{print $1}'",
                             shell=True,capture_output=True,text=True,timeout=5)
            my=str(os.getpid())
            for pid in r.stdout.strip().split():
                if pid!=my:
                    subprocess.run(f"kill -9 {pid}",shell=True,
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    self._actions+=1
        except: pass

    def status(self): return f"{self.stats_str()} {c(CO,self.trend())} {c(CO,f'acc:{self._actions}')}"

RAMGUARD = RamGuard()
