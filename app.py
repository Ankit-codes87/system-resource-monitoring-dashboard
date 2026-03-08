import psutil
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

HISTORY_LEN = 30   # number of readings to keep

# ── Metric collection functions ──────────────────────────────────────────────

def get_cpu_usage() -> float:
    """Return current CPU usage as a percentage (0-100)."""
    return psutil.cpu_percent(interval=1)


def get_memory_usage() -> dict:
    """Return RAM usage stats as a dict with total, used, and percent keys."""
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024 ** 3), 2),
        "used_gb":  round(mem.used  / (1024 ** 3), 2),
        "percent":  mem.percent,
    }


def get_disk_usage(path: str = "/") -> dict:
    """Return disk usage stats for the given path."""
    disk = psutil.disk_usage(path)
    return {
        "total_gb": round(disk.total / (1024 ** 3), 2),
        "used_gb":  round(disk.used  / (1024 ** 3), 2),
        "percent":  disk.percent,
    }


def get_system_uptime() -> str:
    """Return system uptime as a human-readable string."""
    boot_timestamp = psutil.boot_time()
    boot_time      = datetime.fromtimestamp(boot_timestamp)
    uptime_delta   = datetime.now() - boot_time

    total_seconds = int(uptime_delta.total_seconds())
    days          = uptime_delta.days
    hours, rem    = divmod(total_seconds % 86400, 3600)
    minutes, secs = divmod(rem, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)


# ── Helper: colour-coded progress bar ───────────────────────────────────────

def _usage_color(percent: float) -> str:
    if percent < 60:
        return "#4CAF50"   # green
    elif percent < 85:
        return "#FF9800"   # orange
    return "#F44336"       # red


def _render_progress(label: str, percent: float) -> None:
    color = _usage_color(percent)
    st.markdown(
        f"""
        <div style="margin-bottom:6px;">
            <div style="display:flex; justify-content:space-between; font-size:0.85rem;">
                <span>{label}</span>
                <span><b>{percent:.1f}%</b></span>
            </div>
            <div style="background:#e0e0e0; border-radius:6px; height:14px;">
                <div style="width:{percent}%; background:{color}; border-radius:6px; height:14px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Dashboard layout ─────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="System Resource Monitoring Dashboard",
        page_icon="🖥️",
        layout="wide",
    )

    st.title("🖥️ System Resource Monitoring Dashboard")
    st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.divider()

    # ── Initialise history in session state ────────────────────────────────
    if "cpu_history" not in st.session_state:
        st.session_state.cpu_history = []
    if "mem_history" not in st.session_state:
        st.session_state.mem_history = []
    if "time_history" not in st.session_state:
        st.session_state.time_history = []

    # ── Collect metrics ──────────────────────────────────────────────────────
    cpu_pct  = get_cpu_usage()
    mem      = get_memory_usage()
    disk     = get_disk_usage("C:/" if __import__("sys").platform == "win32" else "/")
    uptime   = get_system_uptime()

    # ── Append new readings and trim to last HISTORY_LEN entries ─────────────
    now_label = datetime.now().strftime("%H:%M:%S")
    st.session_state.cpu_history.append(cpu_pct)
    st.session_state.mem_history.append(mem["percent"])
    st.session_state.time_history.append(now_label)
    if len(st.session_state.cpu_history) > HISTORY_LEN:
        st.session_state.cpu_history  = st.session_state.cpu_history[-HISTORY_LEN:]
        st.session_state.mem_history  = st.session_state.mem_history[-HISTORY_LEN:]
        st.session_state.time_history = st.session_state.time_history[-HISTORY_LEN:]

    # ── Top-level KPI cards ──────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        label="⚡ CPU Usage",
        value=f"{cpu_pct:.1f}%",
        delta=None,
        help="Percentage of CPU currently in use across all cores",
    )
    col2.metric(
        label="🧠 Memory Usage",
        value=f"{mem['percent']:.1f}%",
        delta=f"{mem['used_gb']} GB / {mem['total_gb']} GB used",
        help="RAM utilisation",
    )
    col3.metric(
        label="💾 Disk Usage",
        value=f"{disk['percent']:.1f}%",
        delta=f"{disk['used_gb']} GB / {disk['total_gb']} GB used",
        help="Primary disk utilisation",
    )
    col4.metric(
        label="⏱️ System Uptime",
        value=uptime,
        delta=None,
        help="Time elapsed since last system boot",
    )

    st.divider()

    # ── Usage gauges ─────────────────────────────────────────────────────────
    st.subheader("📊 Resource Usage Gauges")
    _render_progress("CPU",    cpu_pct)
    _render_progress("Memory", mem["percent"])
    _render_progress("Disk",   disk["percent"])

    st.divider()

    # ── Usage history line charts ─────────────────────────────────────────────
    st.subheader("📈 Usage History (last 30 readings)")

    history_df = pd.DataFrame(
        {
            "CPU Usage (%)": st.session_state.cpu_history,
            "Memory Usage (%)": st.session_state.mem_history,
        },
        index=st.session_state.time_history,
    )

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.markdown("**⚡ CPU Usage Over Time**")
        st.line_chart(history_df[["CPU Usage (%)"]], height=200, use_container_width=True)
    with chart_col2:
        st.markdown("**🧠 Memory Usage Over Time**")
        st.line_chart(history_df[["Memory Usage (%)"]], height=200, use_container_width=True)

    st.divider()

    # ── Detailed stats table ─────────────────────────────────────────────────
    st.subheader("📋 Detailed Statistics")

    detail_col1, detail_col2 = st.columns(2)

    with detail_col1:
        st.markdown("**CPU**")
        cpu_info = {
            "Physical cores":  psutil.cpu_count(logical=False),
            "Logical cores":   psutil.cpu_count(logical=True),
            "Current usage":   f"{cpu_pct:.1f}%",
            "Max frequency":   f"{psutil.cpu_freq().max:.0f} MHz" if psutil.cpu_freq() else "N/A",
            "Current freq":    f"{psutil.cpu_freq().current:.0f} MHz" if psutil.cpu_freq() else "N/A",
        }
        for k, v in cpu_info.items():
            st.markdown(f"- **{k}:** {v}")

        st.markdown("**Memory**")
        mem_info = {
            "Total RAM":  f"{mem['total_gb']} GB",
            "Used RAM":   f"{mem['used_gb']} GB",
            "Free RAM":   f"{round(psutil.virtual_memory().available / (1024**3), 2)} GB",
            "Usage":      f"{mem['percent']:.1f}%",
        }
        for k, v in mem_info.items():
            st.markdown(f"- **{k}:** {v}")

    with detail_col2:
        st.markdown("**Disk**")
        disk_info = {
            "Total space": f"{disk['total_gb']} GB",
            "Used space":  f"{disk['used_gb']} GB",
            "Free space":  f"{round(psutil.disk_usage('C:/' if __import__('sys').platform == 'win32' else '/').free / (1024**3), 2)} GB",
            "Usage":       f"{disk['percent']:.1f}%",
        }
        for k, v in disk_info.items():
            st.markdown(f"- **{k}:** {v}")

        st.markdown("**System**")
        sys_info = {
            "Boot time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"),
            "Uptime":    uptime,
        }
        for k, v in sys_info.items():
            st.markdown(f"- **{k}:** {v}")

    # ── Auto-refresh ─────────────────────────────────────────────────────────
    st.divider()
    with st.sidebar:
        st.header("⚙️ Settings")
        refresh_interval = st.slider(
            "Refresh interval (seconds)",
            min_value=2,
            max_value=30,
            value=5,
            step=1,
        )
        st.info(f"Dashboard refreshes every **{refresh_interval}s**.")
        st.markdown("---")
        st.markdown("Built with [Streamlit](https://streamlit.io) & [psutil](https://psutil.readthedocs.io)")

    # Trigger automatic rerun after selected interval
    import time
    time.sleep(refresh_interval)
    st.rerun()


if __name__ == "__main__":
    main()


// Sentinal Thoughts......
uptime = get_system_uptime()
    
    # Update history (keep only last HISTORY_LEN readings)
    st.session_state.cpu_history.append(cpu_pct)
    st.session_state.mem_history.append(mem["percent"])
    st.session_state.time_history.append(datetime.now().strftime("%H:%M:%S"))
    
    if len(st.session_state.cpu_history) > HISTORY_LEN:
        st.session_state.cpu_history.pop(0)
        st.session_state.mem_history.pop(0)
        st.session_state.time_history.pop(0)
    
    # Layout columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("CPU Usage", f"{cpu_pct:.1f}%")
        _render_progress("CPU", cpu_pct)
    
    with col2:
        st.metric("RAM Usage", f"{mem['percent']:.1f}%")
        _render_progress("RAM", mem["percent"])
        
        st.metric("RAM Used", f"{mem['used_gb']:.1f} GB")
        st.metric("RAM Total", f"{mem['total_gb']:.1f} GB")
    
    with col3:
        st.metric("Disk Usage", f"{disk['percent']:.1f}%")
        _render_progress("Disk", disk["percent"])
        
        st.metric("Disk Used", f"{disk['used_gb']:.1f} GB")
        st.metric("Disk Total", f"{disk['total_gb']:.1f} GB")
    
    st.divider()
    
    # System info
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("System Information")
        st.metric("System Uptime", uptime)
        st.metric("CPU Usage", f"{cpu_pct:.1f}%")
        st.metric("RAM Usage", f"{mem['percent']:.1f}%")
        st.metric("Disk Usage", f"{disk['percent']:.1f}%")
    
    with col2:
        st.subheader("Usage History")
        if len(st.session_state.time_history) > 0:
            # Create a simple chart using Streamlit's native chart
            import pandas as pd
            import numpy as np
            
            # Create a simple line chart for CPU and Memory history
            chart_data = pd.DataFrame({
                'CPU %': st.session_state.cpu_history,
                'RAM %': st.session_state.mem_history
            }, index=st.session_state.time_history)
            
            st.line_chart(chart_data)
        else:
            st.info("Collecting data...")
    
    # Auto-refresh every 5 seconds
    st.rerun()

if __name__ == "__main__":
    main()
