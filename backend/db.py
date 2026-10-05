import sqlite3, os
from data import COMPONENTS, PROJECTS
PATH = os.path.join(os.path.dirname(__file__), "secondlife.db")
def conn():
    c = sqlite3.connect(PATH); c.row_factory = sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c
def init():
    c = conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS components(id INTEGER PRIMARY KEY, name TEXT UNIQUE, category TEXT, description TEXT, estimated_weight_grams REAL, est_price REAL);
    CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY, component_id INTEGER UNIQUE REFERENCES components(id), quantity INTEGER CHECK(quantity>0), condition TEXT DEFAULT 'Unknown');
    CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, name TEXT UNIQUE, description TEXT, difficulty TEXT, estimated_cost REAL, estimated_waste_reuse_grams REAL, educational_value TEXT, build_steps TEXT);
    CREATE TABLE IF NOT EXISTS project_requirements(id INTEGER PRIMARY KEY, project_id INTEGER REFERENCES projects(id), component_id INTEGER REFERENCES components(id), required_quantity INTEGER);""")
    for line in COMPONENTS.splitlines():
        n, cat, w, p = line.split("|")
        c.execute("INSERT OR IGNORE INTO components(name,category,description,estimated_weight_grams,est_price) VALUES(?,?,?,?,?)", (n, cat, f"{n} ({cat.lower()})", float(w), float(p)))
    ids = {r["name"]: (r["id"], r["estimated_weight_grams"], r["est_price"]) for r in c.execute("SELECT * FROM components")}
    for name, diff, desc, edu, reqs, steps in PROJECTS:
        if c.execute("SELECT 1 FROM projects WHERE name=?", (name,)).fetchone(): continue
        pairs = [(x.split(":")[0], int(x.split(":")[1])) for x in reqs.split(",")]
        cost = sum(ids[n][2] * q for n, q in pairs); waste = sum(ids[n][1] * q for n, q in pairs)
        cur = c.execute("INSERT INTO projects(name,description,difficulty,estimated_cost,estimated_waste_reuse_grams,educational_value,build_steps) VALUES(?,?,?,?,?,?,?)", (name, desc, diff, cost, waste, edu, steps))
        for n, q in pairs: c.execute("INSERT INTO project_requirements(project_id,component_id,required_quantity) VALUES(?,?,?)", (cur.lastrowid, ids[n][0], q))
    c.commit(); c.close()
def projects():
    c = conn(); out = []
    for p in c.execute("SELECT * FROM projects ORDER BY id"):
        reqs = [dict(component_id=r["component_id"], name=r["name"], required=r["required_quantity"], weight=r["estimated_weight_grams"], price=r["est_price"], category=r["category"])
                for r in c.execute("SELECT pr.*, c.name, c.estimated_weight_grams, c.est_price, c.category FROM project_requirements pr JOIN components c ON c.id=pr.component_id WHERE project_id=?", (p["id"],))]
        out.append({**dict(p), "build_steps": p["build_steps"].split(";"), "requirements": reqs})
    c.close(); return out
