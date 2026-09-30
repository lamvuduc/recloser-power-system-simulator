def fnum(data, key, default):
    try:
        return float(data.get(key, default))
    except (TypeError, ValueError):
        return float(default)

def inum(data, key, default):
    try:
        return max(0, int(float(data.get(key, default))))
    except (TypeError, ValueError):
        return int(default)

def simulate(data):
    # System / fault
    nominal_v = fnum(data, "nominal_v", 110)
    fault_current = fnum(data, "fault_current", 2.5)
    pickup = fnum(data, "pickup", 2.0)
    fault_duration = fnum(data, "fault_duration", 0.35)

    # Reclosing
    dead_time = max(0.1, fnum(data, "dead_time", 2.0))
    max_reclose = inum(data, "max_reclose", 2)

    # Closing checks
    bus_v = fnum(data, "bus_v", 110)
    line_v = fnum(data, "line_v", 109)
    bus_f = fnum(data, "bus_f", 50)
    line_f = fnum(data, "line_f", 50)
    phase_angle = abs(fnum(data, "phase_angle", 5))

    min_bus_v_pu = fnum(data, "min_bus_v_pu", 0.90)
    max_delta_v_pu = fnum(data, "max_delta_v_pu", 0.10)
    max_delta_f = fnum(data, "max_delta_f", 0.20)
    max_phase = fnum(data, "max_phase", 10)

    fault_clears = str(data.get("fault_clears", "yes")).lower() == "yes"

    # Protection pickup
    overcurrent = fault_current > pickup

    # Synchronism / closing checks
    bus_v_pu = bus_v / nominal_v if nominal_v else 0
    line_v_pu = line_v / nominal_v if nominal_v else 0
    delta_v_pu = abs(bus_v - line_v) / nominal_v if nominal_v else 999
    delta_f = abs(bus_f - line_f)

    bus_voltage_ok = bus_v_pu >= min_bus_v_pu
    line_voltage_ok = line_v_pu >= min_bus_v_pu
    voltage_diff_ok = delta_v_pu <= max_delta_v_pu
    frequency_ok = delta_f <= max_delta_f
    phase_ok = phase_angle <= max_phase

    conditions_ok = (
        bus_voltage_ok and line_voltage_ok and voltage_diff_ok
        and frequency_ok and phase_ok
    )

    events = [
        {"time":"00.00 s","type":"normal","text":"System initialized — CB CLOSED, line energized"},
        {"time":"00.10 s","type":"info","text":f"Pre-fault: {nominal_v:.0f} kV / {bus_f:.2f} Hz"},
    ]

    if not overcurrent:
        events.append({"time":"00.20 s","type":"success","text":
                       f"No trip — I = {fault_current:.2f} kA is below pickup {pickup:.2f} kA"})
        return result("NORMAL", "SYSTEM NORMAL", events, 0, {
            "overcurrent": False,
            "bus_voltage_ok": bus_voltage_ok,
            "line_voltage_ok": line_voltage_ok,
            "voltage_diff_ok": voltage_diff_ok,
            "frequency_ok": frequency_ok,
            "phase_ok": phase_ok
        }, {
            "bus_v_pu": bus_v_pu, "line_v_pu": line_v_pu,
            "delta_v_pu": delta_v_pu, "delta_f": delta_f
        })

    events += [
        {"time":f"{fault_duration:.2f} s","type":"danger",
         "text":f"FAULT DETECTED — I = {fault_current:.2f} kA > pickup {pickup:.2f} kA"},
        {"time":f"{fault_duration+0.10:.2f} s","type":"warning",
         "text":"Protection trip command issued"},
        {"time":f"{fault_duration+0.20:.2f} s","type":"warning",
         "text":"CB OPEN — faulted section isolated"},
        {"time":f"{fault_duration+0.25:.2f} s","type":"info",
         "text":"Line side becomes de-energized; recloser starts dead-time timer"},
    ]

    if not fault_clears:
        # A persistent fault means the fault will return on each attempted close.
        for attempt in range(1, max_reclose + 1):
            t = dead_time * attempt
            events.append({"time":f"{t:.2f} s","type":"warning",
                           "text":f"REclose attempt {attempt} — closing checks passed, but fault is still present"})
            events.append({"time":f"{t+0.15:.2f} s","type":"danger",
                           "text":"Fault current returns — CB TRIPS again"})
        events.append({"time":"FINAL","type":"danger",
                       "text":f"LOCKOUT — {max_reclose} reclose attempt(s) exhausted"})
        events.append({"time":"FINAL","type":"danger",
                       "text":"Automatic reclosing blocked — operator intervention required"})
        return result("LOCKOUT", "LOCKOUT — OPERATOR REQUIRED", events, max_reclose, {
            "overcurrent": True, "bus_voltage_ok": bus_voltage_ok,
            "line_voltage_ok": line_voltage_ok, "voltage_diff_ok": voltage_diff_ok,
            "frequency_ok": frequency_ok, "phase_ok": phase_ok
        }, {"bus_v_pu":bus_v_pu,"line_v_pu":line_v_pu,"delta_v_pu":delta_v_pu,"delta_f":delta_f})

    # Transient fault: after trip the fault disappears. The line is de-energized,
    # so the line-side voltage is checked against the configured closing scenario.
    events.append({"time":f"{dead_time:.2f} s","type":"info","text":"Dead time expired — checking closing conditions"})
    events.append({"time":f"{dead_time+0.05:.2f} s","type":"info",
                   "text":f"Bus: {bus_v:.1f} kV | Line: {line_v:.1f} kV | ΔV: {delta_v_pu*100:.1f}%"})
    events.append({"time":f"{dead_time+0.08:.2f} s","type":"info",
                   "text":f"Δf: {delta_f:.2f} Hz | Δφ: {phase_angle:.1f}°"})

    if not conditions_ok:
        reasons = []
        if not bus_voltage_ok: reasons.append("bus voltage low")
        if not line_voltage_ok: reasons.append("line voltage low")
        if not voltage_diff_ok: reasons.append("voltage difference too high")
        if not frequency_ok: reasons.append("frequency difference too high")
        if not phase_ok: reasons.append("phase-angle difference too high")
        events.append({"time":f"{dead_time+0.15:.2f} s","type":"danger",
                       "text":"AUTO RECLOSE BLOCKED — " + ", ".join(reasons)})
        events.append({"time":"FINAL","type":"danger",
                       "text":"Alarm sent to operator — manual assessment required"})
        return result("OPERATOR", "AUTO RECLOSE BLOCKED", events, 0, {
            "overcurrent": True, "bus_voltage_ok": bus_voltage_ok,
            "line_voltage_ok": line_voltage_ok, "voltage_diff_ok": voltage_diff_ok,
            "frequency_ok": frequency_ok, "phase_ok": phase_ok
        }, {"bus_v_pu":bus_v_pu,"line_v_pu":line_v_pu,"delta_v_pu":delta_v_pu,"delta_f":delta_f})

    events += [
        {"time":f"{dead_time+0.15:.2f} s","type":"success","text":"Closing conditions PASS — permissive received"},
        {"time":f"{dead_time+0.25:.2f} s","type":"success","text":"AUTO RECLOSE — CB CLOSED"},
        {"time":f"{dead_time+0.55:.2f} s","type":"success","text":"Fault cleared — current returned to normal"},
        {"time":f"{dead_time+0.70:.2f} s","type":"success","text":"SYSTEM RESTORED — Recloser ready"},
    ]
    return result("SUCCESS", "AUTO RECLOSE SUCCESS", events, 1, {
        "overcurrent": True, "bus_voltage_ok": bus_voltage_ok,
        "line_voltage_ok": line_voltage_ok, "voltage_diff_ok": voltage_diff_ok,
        "frequency_ok": frequency_ok, "phase_ok": phase_ok
    }, {"bus_v_pu":bus_v_pu,"line_v_pu":line_v_pu,"delta_v_pu":delta_v_pu,"delta_f":delta_f})

def result(outcome, label, events, count, checks, metrics):
    return {
        "ok": True,
        "outcome": outcome,
        "outcome_label": label,
        "events": events,
        "reclose_count": count,
        "checks": checks,
        "metrics": metrics
    }
