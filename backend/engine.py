"""Deterministic, explainable matching engine (no external services)."""
def evaluate(project, inv):
    """project['requirements']: [{component_id,name,required,weight,price}]; inv: {component_id: qty}."""
    rows, ratios, used_units, req_units, waste, cost = [], [], 0, 0, 0.0, 0.0
    for r in project["requirements"]:
        have = inv.get(r["component_id"], 0)
        used = min(have, r["required"])
        ratio = min(have / r["required"], 1)
        status = "full" if ratio == 1 else "partial" if ratio > 0 else "missing"
        rows.append({**r, "available": have, "used": used, "fulfillment": round(ratio * 100), "status": status})
        ratios.append(ratio); used_units += used; req_units += r["required"]
        waste += used * r["weight"]; cost += (r["required"] - used) * r["price"]
    score = round(sum(ratios) / len(ratios) * 100, 1) if ratios else 0.0
    full = sum(x["status"] == "full" for x in rows)
    partial = sum(x["status"] == "partial" for x in rows)
    missing = sum(x["status"] == "missing" for x in rows)
    if score == 100:
        completion_status = "READY TO BUILD"
        summary = f"Complete match! You have all {len(rows)} required component types ({used_units}/{req_units} units)."
        why = [
            f"✓ {full} of {len(rows)} required component types available in full",
            "✓ All required component quantities satisfied",
            "✓ Everything you need is already available in your drawer",
            f"✓ Keeps about {round(waste)}g of electronic material in active circular use"
        ]
    elif score >= 70:
        completion_status = "ALMOST THERE"
        summary = f"You're almost there! You hold {full} of {len(rows)} required component types in full."
        missing_names = [r["name"] for r in rows if r["status"] == "missing"]
        why = [
            f"✓ {full} of {len(rows)} required component types available ({used_units}/{req_units} units)",
            f"✓ {score}% of total project requirements satisfied",
            f"○ Need {missing} part(s): {', '.join(missing_names) if missing_names else 'extra units'}",
            f"✓ Additional cost to complete: ₹{round(cost)}"
        ]
    elif score > 0:
        completion_status = "PARTIAL MATCH"
        summary = f"You hold {used_units} of {req_units} required component units."
        why = [
            f"✓ {used_units} of {req_units} total component units available",
            f"✓ {score}% feasibility score based on inventory",
            f"○ Additional cost to complete: ₹{round(cost)}"
        ]
    else:
        completion_status = "NOT CURRENTLY FEASIBLE"
        summary = "No components in inventory match this project's requirements."
        why = ["○ No matching components in inventory"]

    return {"id": project["id"], "name": project["name"], "description": project["description"],
            "difficulty": project["difficulty"], "score": score, "summary": summary, "requirements": rows,
            "matched_count": full, "partial_count": partial, "missing_count": missing,
            "completion_status": completion_status, "why_recommended": why,
            "waste_reused_g": round(waste), "additional_cost": round(cost), "low_match": score < 30}

def recommend(projects, inv, include_zero=False):
    out = [evaluate(p, inv) for p in projects]
    if not include_zero:
        out = [o for o in out if o["score"] > 0]
    return sorted(out, key=lambda o: (-o["score"], -o["matched_count"], o["missing_count"], o["name"]))
