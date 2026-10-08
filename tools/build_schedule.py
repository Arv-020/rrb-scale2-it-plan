import json, re, sys, datetime as dt
from collections import defaultdict, deque

SRC = sys.argv[1]
OUT = sys.argv[2]
d = json.load(open(SRC))

SUBJ = [
    ("Professional Knowledge - IT - MAINS", "PK"), ("Computer Awareness", "C"),
    ("Banking Awareness", "FA"), ("Financial Awareness Live", "FA"), ("Financial Awareness", "FA"),
    ("General Economy", "FA"), ("Government Schemes", "GS"), ("Current Affairs 2026", "CA"),
    ("Start Here", "S"), ("English", "E"), ("Reasoning", "R"), ("Quant", "Q"), ("Hindi", "H"),
]

def subj_of(meta):
    for name, code in SUBJ:
        if f" {name} " in f" {meta} ":
            return code
    return None

upcoming = {}
for u in d["Upcoming"]:
    if u["when"]:
        upcoming[(u["title"].strip(), subj_of(u["meta"]))] = dt.datetime.strptime(u["when"], "%b %d, %Y %I:%M %p")

def parse(c):
    meta = c["meta"]
    watched = meta.startswith("Watched")
    live = meta.startswith("Live ")
    subj = subj_of(meta)
    m = re.search(r"(?:(\d+)h )?(\d+)m", meta.replace(c["title"], ""))
    mins = (int(m.group(1) or 0) * 60 + int(m.group(2))) if m else 60
    rel = upcoming.get((c["title"].strip(), subj))
    return dict(title=c["title"].strip(), subj=subj, mins=mins, watched=watched, live=live,
                release=rel.date().isoformat() if rel else None)

classes = [parse(c) for c in d["All"]]
LINKS = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else []
for c, l in zip(classes, LINKS):
    assert l[0] == c["title"], (l[0], c["title"])
    c["cid"], c["pdf"], c["hasq"] = l[1], l[2], l[3]

# ---------- mode rules (speed / notes / skip) ----------
E_GRAMMAR_NOTES = {"Confusing forms of Verbs", "Practice Questions of Verbs", "Subject-Verb & Agreement - I",
    "Subject-Verb & Agreement - II", "Indefinite Tenses", "Perfect Tenses", "Continuous and Perfect Continuous Tense",
    "Special Cases of Tense", "Noun & Numbers", "Noun & Cases", "Noun Miscellaneous Rules", "Personal Pronouns",
    "Possessive & Reflexive Pronoun", "Relative Pronoun", "Pronouns (Miscellaneous Rules)", "Adjectives - I",
    "Adverbs - I", "Adjectives - II", "Adverbs - II", "Articles - I", "Articles - II", "Articles Practice Set",
    "Conditional Sentences", "Gerunds & Infinitives", "Bare Infinitives", "Conjunctions", "Prepositions - I",
    "Prepositions - II"}
C_SKIP = {"Introduction to Computer Networks": "same as PK networking", "OSI Model & TCP/IP Model": "covered in PK",
    "IP Addressing": "covered in PK", "Subnet Mask, Mac Address and ARP": "covered in PK",
    "RARP, DHCP, Switching, Routing": "covered in PK", "Common Network Protocols": "covered in PK",
    "Network Devices (Switch, Hub, Repeater,Router, Modem)": "covered in PK",
    "LAN, MAN, WAN, Network Security": "covered in PK", "DBMS": "covered in PK (7 DBMS classes)",
    "Programming Basics": "covered in PK (C, Java, Python)", "Operating Systems -1": "covered in PK OS classes",
    "Operating Systems -2": "covered in PK OS classes"}
C_NOTES = {"Introduction to Computer", "Types of Computers", "Organization of Computers", "Computer Ports",
    "Output Devices (Monitor, Printer, Speakers, etc.)", "Storage Devices (Hard Disk, SSD, CD/DVD, USB Drives)",
    "Memory Types (RAM, ROM, Cache, Virtual Memory)", "Computer Software",
    "Computer Abbreviations (CPU, RAM, ROM, etc.)", "Computer File Extensions (.docx, .xlsx, .pptx, etc.)",
    "Keyboard shortcuts and their uses of computer"}
FA_DUP_NOTES = {"Money Market & its Instruments": "repeat of Money Market 1 & 2",
    "Capital Markets & its Instruments Part 1": "repeat of Capital Market 1",
    "Capital Markets & its Instruments Part 2": "repeat of Capital Market 2",
    "Inflation & its types": "repeat of Inflation 1 & 2",
    "National Income : GDP GNP GDP Deflator": "repeat of National Income",
    "Payments & Settlement Systems Part 1 NPCI , UPI , AePS": "overlaps Payment Systems (Banking Awareness)"}
CA_KEEP = re.compile(r"(July|August|September) 2026: (Banking, Business and Economy|RBI news and circulars)"
                     r"|(June|July|August|September) Month Monthly Affairs|Weekly CA - Session \d \(\d+(st|nd|rd|th) - \d+(st|nd|rd|th), (September|October)\)")

def mode_for(c):
    s, t = c["subj"], c["title"]
    if s == "H": return ("skip", "Hindi not needed, you take English")
    if s == "S": return ("watch", 1.5) if not c["watched"] else ("done", None)
    if c["watched"]: return ("done", None)
    if s == "Q":
        if c["mins"] > 95: return ("watch", 2.0)
        return ("watch", 1.75 if c["mins"] > 80 else 1.5)
    if s == "R": return ("watch", 1.75 if ("Mains" in t or t.startswith("Coded")) else 1.5)
    if s == "PK": return ("watch", 2.0)
    if s == "E":
        if t in E_GRAMMAR_NOTES: return ("notes", "grammar: Notes + Imp Qs")
        if t in ("Connectors Rules & Practice Questions", "Vocabulary - II ( Idioms & Phrasal Verbs)", "Miscellaneous Questions", "Sample Mock"):
            return ("notes", "Notes + Imp Qs (do the practice, skip the video)")
        if t.startswith("Vocabulary") or t.startswith("Connectors"): return ("watch", 2.0)
        return ("watch", 1.5)
    if s == "C":
        if t in C_SKIP: return ("skip", C_SKIP[t])
        if t in C_NOTES: return ("notes", "facts: Notes + Quiz")
        return ("watch", 2.0)
    if s == "FA":
        if t in FA_DUP_NOTES: return ("notes", FA_DUP_NOTES[t])
        return ("watch", 2.0)
    if s == "GS": return ("notes", "Summary Notes + Cards")
    if s == "CA":
        return ("watch", 2.0) if CA_KEEP.search(t) else ("skip", "older than July, or not finance-related (Daily CA Quiz covers general news)")
    return ("skip", "")

STATUS = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {"resume": []}
RESUME = set(STATUS.get("resume", []))
items = []
for i, c in enumerate(classes):
    mode, extra = mode_for(c)
    c["mode"] = mode
    if mode == "watch":
        c["speed"] = extra
        PRACTICE = {"Q": 15, "R": 25, "PK": 15, "FA": 10, "E": 20, "C": 10, "CA": 5, "S": 0}
        pr = PRACTICE.get(c["subj"], 10)
        if c["title"].startswith("How to Crack"): pr = 0
        w = int(round(c["mins"] / extra / 5.0) * 5)
        if c["title"] in RESUME:
            w = max(5, int(round(w / 2 / 5.0) * 5)); c["half"] = 1
        c["watchm"], c["prac"] = w, pr
        c["est"] = w + pr
    elif mode == "notes":
        c["why"] = extra
        c["est"] = 25
    else:
        c["why"] = extra
        c["est"] = 0
    c["id"] = f"c{i}"
    items.append(c)

# Quant: put "How to Crack Quant" first, resume Calculation Tricks 2 next
queues = defaultdict(deque)
start_here_q = [c for c in items if c["subj"] == "S" and c["mode"] == "watch"]
order = start_here_q + [c for c in items if c["subj"] != "S"]
for c in start_here_q: c["subj"] = "Q"
BUNDLES = [
 ("E", "Grammar notes: Verbs", ["Confusing forms of Verbs", "Practice Questions of Verbs"]),
 ("E", "Grammar notes: Subject-Verb Agreement I & II", ["Subject-Verb & Agreement - I", "Subject-Verb & Agreement - II"]),
 ("E", "Grammar notes: Tenses (4 classes)", ["Indefinite Tenses", "Perfect Tenses", "Continuous and Perfect Continuous Tense", "Special Cases of Tense"]),
 ("E", "Grammar notes: Nouns (3 classes)", ["Noun & Numbers", "Noun & Cases", "Noun Miscellaneous Rules"]),
 ("E", "Grammar notes: Pronouns (4 classes)", ["Personal Pronouns", "Possessive & Reflexive Pronoun", "Relative Pronoun", "Pronouns (Miscellaneous Rules)"]),
 ("E", "Grammar notes: Adjectives & Adverbs (4 classes)", ["Adjectives - I", "Adverbs - I", "Adjectives - II", "Adverbs - II"]),
 ("E", "Grammar notes: Articles (3 classes)", ["Articles - I", "Articles - II", "Articles Practice Set"]),
 ("E", "Grammar notes: Conditionals, Gerunds, Infinitives", ["Conditional Sentences", "Gerunds & Infinitives", "Bare Infinitives"]),
 ("E", "Grammar notes: Conjunctions & Prepositions", ["Conjunctions", "Prepositions - I", "Prepositions - II"]),
 ("C", "Computer basics notes: intro, types, organisation, ports", ["Introduction to Computer", "Types of Computers", "Organization of Computers", "Computer Ports"]),
 ("C", "Computer basics notes: output, storage, memory, software", ["Output Devices (Monitor, Printer, Speakers, etc.)", "Storage Devices (Hard Disk, SSD, CD/DVD, USB Drives)", "Memory Types (RAM, ROM, Cache, Virtual Memory)", "Computer Software"]),
 ("C", "Computer facts notes: abbreviations, file extensions, shortcuts", ["Computer Abbreviations (CPU, RAM, ROM, etc.)", "Computer File Extensions (.docx, .xlsx, .pptx, etc.)", "Keyboard shortcuts and their uses of computer"]),
]
by_title = {}
for c in order:
    by_title.setdefault((c["subj"], c["title"]), c)
bundled = set()
bundle_items = []
for subj, name, titles in BUNDLES:
    members = [by_title[(subj, t)] for t in titles if (subj, t) in by_title]
    for m in members: bundled.add(m["id"])
    rels = [m["release"] for m in members if m["release"]]
    bundle_items.append({"id": "b" + members[0]["id"], "subj": subj, "title": name, "mode": "notes",
        "why": "Notes + Imp Qs for " + ", ".join(m["title"] for m in members), "est": 15 + 8 * len(members),
        "mins": sum(m["mins"] for m in members), "release": max(rels) if rels else None, "first": members[0]["id"],
        "members": [{"t": m["title"], "cid": m.get("cid")} for m in members]})
gs = [c for c in order if c["subj"] == "GS"]
for i in range(0, len(gs), 3):
    grp = gs[i:i+3]
    for m in grp: bundled.add(m["id"])
    nums = [re.search(r"Part (\d+)", m["title"]).group(1) for m in grp]
    bundle_items.append({"id": "b" + grp[0]["id"], "subj": "GS", "title": f"Govt Schemes Parts {nums[0]}–{nums[-1]}: Summary Notes + Cards",
        "mode": "notes", "why": "; ".join(re.sub(r"^Government Scheme Part \d+ - ", "", m["title"]) for m in grp), "est": 40,
        "mins": sum(m["mins"] for m in grp), "release": None, "first": grp[0]["id"],
        "members": [{"t": m["title"], "cid": m.get("cid")} for m in grp]})
first_pos = {}
for b in bundle_items: first_pos[b["first"]] = b
for c in order:
    if c["id"] in first_pos:
        queues[first_pos[c["id"]]["subj"]].append(first_pos[c["id"]])
    elif c["id"] in bundled:
        continue
    elif c["mode"] in ("watch", "notes"):
        queues[c["subj"]].append(c)

INITIAL_QUEUES = {k: list(v) for k, v in queues.items()}

# ---------- full library: every class in the course, with its status ----------
SECTION_OF = {c["id"]: next((name for name, code in SUBJ if f" {name} " in f" {d['All'][int(c['id'][1:])]['meta']} "), "") for c in items}
INTRO_SUBJ = {"How to Crack IT Mains with this course": "PK", "How to Crack Reasoning with this course": "R",
              "How to Crack English with this course": "E", "How to Crack Computer Awareness with this course": "C",
              "How to Crack Quant with this course": "Q"}
def default_speed(s, t, mins):
    if s == "Q": return 2.0 if mins > 95 else (1.75 if mins > 80 else 1.5)
    if s == "R": return 1.75 if ("Mains" in t or t.startswith("Coded")) else 1.5
    if s == "E": return 1.5
    return 2.0
PRACTICE_MIN = {"Q": 15, "R": 25, "PK": 15, "FA": 10, "E": 20, "C": 10, "CA": 5, "GS": 10, "H": 10}
bundle_of = {}
for b in bundle_items:
    for m in b["members"]:
        bundle_of[(b["subj"], m["t"])] = b
lib = []
for c in items:
    sc = INTRO_SUBJ.get(c["title"], c["subj"]) if c["subj"] in ("S", "Q") else c["subj"]
    sp = c.get("speed") or default_speed(sc, c["title"], c["mins"])
    w = c.get("watchm") or max(5, int(round(c["mins"] / sp / 5.0) * 5))
    pr = c.get("prac") if c.get("prac") is not None else (0 if c["title"].startswith("How to Crack") else PRACTICE_MIN.get(sc, 10))
    e = {"id": c["id"], "idx": int(c["id"][1:]), "s": sc, "sec": SECTION_OF[c["id"]], "t": c["title"], "len": c["mins"],
         "sp": sp, "w": w, "pr": pr, "est": w + pr}
    if c.get("cid"): e["cid"] = c["cid"]
    elif c.get("release"): e["rel"] = c["release"]
    if c.get("hasq"): e["q"] = 1
    if c.get("half"): e["half"] = 1
    b = bundle_of.get((sc, c["title"]))
    if c["mode"] == "done": e["st"] = "watched"
    elif b: e["st"] = "bundle"; e["bid"] = b["id"]; e["bt"] = b["title"]
    elif c["mode"] == "skip": e["st"] = "skip"; e["why"] = c.get("why", "")
    else: e["st"] = "plan"
    lib.append(e)
LIB_BY_ID = {e["id"]: e for e in lib}
# ---------- calendar ----------
START, END = dt.date(2026, 10, 8), dt.date(2026, 12, 19)
LEARN_END = dt.date(2026, 12, 4)
FREE = "https://u1.oliveboard.in/tests/?c={}&i=banking"
GO = lambda c, n: f"https://u1.oliveboard.in/exams/tests/part.php?c={c}&testid={n}"
TEST_START = {"ibpsrrbscp": 1, "ibpsrrbasp": 1, "rrbscale2offen": 21, "sbipopre19": 1, "ibpsprelim": 1, "licjem": 1, "sbiclerkpre2020": 1,
              "ibpsclerkprelim": 1, "rbiassistantp": 1, "nicl": 1, "uiicao": 1, "niacl": 1, "licap": 1}
TESTS = {
 "2026-10-11": [("IBPS RRB Officer Prelims 1 (free): Reasoning + Quant, 45 min, then 30 min review", 75, (FREE.format("ibpsrrbscp"), GO("ibpsrrbscp", TEST_START["ibpsrrbscp"])))],
 "2026-10-18": [("IBPS RRB Assistant Prelims 1 (free): Reasoning + Quant, 45 min, then 30 min review", 75, (FREE.format("ibpsrrbasp"), GO("ibpsrrbasp", TEST_START["ibpsrrbasp"])))],
 "2026-10-25": [("RRB Scale II General Officer Mock 1 (free): 200 Qs, 2 hours, same non-IT sections as yours, then 1h review", 180, (FREE.format("rrbscale2offen"), GO("rrbscale2offen", TEST_START["rrbscale2offen"])))],
 "2026-11-01": [("SBI PO Prelims 1 (free): English + Quant + Reasoning, 1 hour, then 40 min review", 100, (FREE.format("sbipopre19"), GO("sbipopre19", TEST_START["sbipopre19"])))],
 "2026-11-08": [("★ Course Mock 1: RRB Scale2 Officer IT 1 (150 min), then 1h review", 210, (FREE.format("rrbscale2offit"), GO("rrbscale2offit", 1)))],
 "2026-11-14": [("IBPS PO Prelims 1 (free): 1 hour, then 40 min review", 100, (FREE.format("ibpsprelim"), GO("ibpsprelim", TEST_START["ibpsprelim"])))],
 "2026-11-15": [("LIC AAO IT Mains 1 (free): IT professional knowledge, 2 hours, then 30 min review", 150, (FREE.format("licjem"), GO("licjem", TEST_START["licjem"])))],
 "2026-11-21": [("SBI Clerk Prelims 1 (free): 1 hour, then 40 min review", 100, (FREE.format("sbiclerkpre2020"), GO("sbiclerkpre2020", TEST_START["sbiclerkpre2020"])))],
 "2026-11-22": [("★ Course Mock 2: RRB Scale2 Officer IT 2, then 1h review", 210, (FREE.format("rrbscale2offit"), GO("rrbscale2offit", 2)))],
 "2026-11-29": [("★ Course Mock 3: RRB Scale2 Officer IT 3, then 1h review", 210, (FREE.format("rrbscale2offit"), GO("rrbscale2offit", 3)))],
 "2026-12-06": [("★ Course Mock 4: RRB Scale2 Officer IT 4, then 1h review", 210, (FREE.format("rrbscale2offit"), GO("rrbscale2offit", 4)))],
 "2026-12-13": [("★ Course Mock 5: RRB Scale2 Officer IT 5, then 1h review", 210, (FREE.format("rrbscale2offit"), GO("rrbscale2offit", 5)))],
}
PHASE2_SECTIONALS = [  # free one-hour prelims tests, used as 30-min single-section drills
 ("IBPS Clerk Prelims 1 (free): attempt Reasoning only, 30-min timer", (FREE.format("ibpsclerkprelim"), GO("ibpsclerkprelim", TEST_START["ibpsclerkprelim"]))),
 ("RBI Assistant Prelims 1 (free): attempt Quant only, 30-min timer", (FREE.format("rbiassistantp"), GO("rbiassistantp", TEST_START["rbiassistantp"]))),
 ("NICL AO Prelims 1 (free): attempt English only, 30-min timer", (FREE.format("nicl"), GO("nicl", TEST_START["nicl"]))),
 ("UIIC AO Prelims 1 (free): attempt Reasoning only, 30-min timer", (FREE.format("uiicao"), GO("uiicao", TEST_START["uiicao"]))),
 ("NIACL AO Prelims 1 (free): attempt Quant only, 30-min timer", (FREE.format("niacl"), GO("niacl", TEST_START["niacl"]))),
 ("LIC AAO Prelims 1 (free): attempt Reasoning + Quant, 40-min timer", (FREE.format("licap"), GO("licap", TEST_START["licap"]))),
]

ROT = {0: ["R", "PK", "FA"], 1: ["R", "FA", "E"], 2: ["R", "PK", "FA"], 3: ["R", "PK", "C", "E"],
       4: ["R", "FA", "CA"], 5: ["R", "PK", "GS", "FA", "E", "CA", "C"], 6: ["FA", "GS", "R", "PK", "CA", "E"]}
FALLBACK = ["FA", "PK", "R", "E", "C", "CA", "GS"]

def available(c, day, slot):
    if not c["release"]: return True
    r = dt.date.fromisoformat(c["release"])
    return r < day if slot == "am" else r <= day

def take(subj, day, slot, cap, tol=15):
    q = queues[subj]
    for i, c in enumerate(list(q)[:4]):
        if not available(c, day, slot):
            continue
        if c["est"] > cap + tol:
            return None
        del q[i]
        return c
    return None

def entry(c):
    e = {"id": c["id"], "s": c["subj"], "t": c["title"], "m": c["mode"], "est": c["est"], "len": c["mins"]}
    if "watchm" in c: e["w"], e["pr"] = c["watchm"], c["prac"]
    if c.get("cid"): e["cid"] = c["cid"]
    elif c.get("release"): e["rel"] = c["release"]
    if c.get("hasq"): e["q"] = 1
    if c.get("members"): e["mem"] = c["members"]
    if c.get("half"): e["half"] = 1
    if c["mode"] == "watch": e["sp"] = c["speed"]
    else: e["why"] = c.get("why", "")
    return e

CV = [("Number Series", "Number Series"), ("Simplification", "Simplification and Approximation"), ("Approximation", "Simplification and Approximation"),
      ("VBODMAS", "Simplification and Approximation"), ("Calculation", "Shortcuts and Speed Maths"), ("Square", "Shortcuts and Speed Maths"),
      ("Number System", "Number system"), ("Percentage", "Ratio, proportion and partnerships"), ("Ages", "Age problems"), ("Partnership", "Ratio, proportion and partnerships"),
      ("Mixture", "Averages and alligation"), ("Average", "Averages and alligation"), ("Profit", "Profit and Loss"), ("Interest", "Interest"), ("SI and CI", "Interest"),
      ("Quadratic", "Algebra"), ("Algebra", "Algebra"), ("Time & Work", "Time & Work"), ("Pipes", "Time & Work"), ("Speed", "Speed Time & Distance"),
      ("Trains", "Speed Time & Distance"), ("Boats", "Speed Time & Distance"), ("Tabular", "DI Part 1 - Tables and Caselets"), ("Caselet", "DI Part 1 - Tables and Caselets"),
      ("Bar Graph", "DI Part 2 - Graphs"), ("Line Graph", "DI Part 2 - Graphs"), ("Pie", "DI Part 3 - Charts"), ("Mixed DI", "DI Part 3 - Charts"),
      ("Permutation", "Permutations and Probability"), ("Probability", "Permutations and Probability"), ("Mensuration", "Mensuration 2D"),
      ("Quantity", "Data Sufficiency & Comparison"), ("Data Sufficiency", "Data Sufficiency & Comparison")]
def cv_topic(title):
    for k, v in CV:
        if k.lower() in title.lower(): return v
    return None

days = []
day = START
sect_i = 0
while day <= END:
    wd = day.weekday()
    iso = day.isoformat()
    rec = {"date": iso, "am": [], "pm": [], "tests": [], "tasks": []}
    # ---- morning: Quant only ----
    c = take("Q", day, "am", 60, tol=20)
    morning_q = c
    if c:
        rec["am"].append(entry(c))
    elif day <= LEARN_END:
        rec["tasks"].append({"slot": "am", "id": f"amq-{iso}", "t": "Quant practice: Imp Qs of your last 2 Quant classes + 10 calculation questions, timed"})
    else:
        rec["tasks"].append({"slot": "am", "id": f"amq-{iso}", "t": "Quant drill: 1 DI set + 10 arithmetic questions in 20 min, then check every wrong answer"})
    # ---- night / weekend ----
    weekend = wd >= 5
    cap = 300 if weekend else 175
    if morning_q and not morning_q["title"].startswith("How to Crack"):
        topic = cv_topic(morning_q["title"])
        where = f"10 Qs from Concept Videos › {topic} (Quiz / Imp Qs)" if topic else "the class's Imp Qs again, timed"
        rec["tasks"].append({"slot": "pm0", "id": f"qp-{iso}", "t": f"Quant practice on this morning's topic ({morning_q['title']}): redo your wrong Quiz questions, then {where}", "est": 20, "cid": morning_q.get("cid"), "cv": topic})
        cap -= 20
    if wd == 5 and day <= LEARN_END:
        rec["tasks"].append({"slot": "pm0", "id": f"wk-{iso}", "t": "Weekly revision: redo every question in this week's error log, then the Cards of this week's Banking/FA and PK classes", "est": 45})
        cap -= 45
    for t in TESTS.get(iso, []):
        rec["tests"].append({"id": f"test-{iso}", "t": t[0], "est": t[1], "url": t[2]})
        cap -= t[1]
    if day <= LEARN_END:
        rot = ROT[wd] + [x for x in FALLBACK if x not in ROT[wd]]
        per = defaultdict(int)
        maxper = 2
        ptr = 0
        while cap > 20:
            got = False
            for k in range(len(rot)):
                s_ = rot[(ptr + k) % len(rot)]
                if per[s_] >= (4 if s_ == "GS" else maxper):
                    continue
                c = take(s_, day, "pm", cap)
                if c:
                    rec["pm"].append(entry(c)); cap -= c["est"]; per[s_] += 1
                    ptr = (ptr + k + 1) % len(rot)
                    got = True
                    break
            if not got:
                break
    else:
        # practice + revision phase: at most ~100 min of leftover classes a night
        budget = 100
        for s_ in FALLBACK + ["R", "Q"]:
            while budget > 20:
                c = take(s_, day, "pm", budget, tol=10)
                if not c: break
                rec["pm"].append(entry(c)); budget -= c["est"]
        if day <= dt.date(2026, 12, 13):
            if not TESTS.get(iso):
                name, url = PHASE2_SECTIONALS[sect_i % len(PHASE2_SECTIONALS)] if sect_i < len(PHASE2_SECTIONALS) else \
                    (["Reasoning", "PK-IT", "Quant", "English", "Financial Awareness"][sect_i % 5] + " sectional: 40 Qs from class Quizzes / Imp Qs, strict 30-min timer (FA: 15 min)", None)
                rec["tasks"].append({"slot": "pm", "id": f"sec-{iso}", "t": name, "url": url})
                sect_i += 1
            unit = ["Networks + Security", "DBMS + SQL", "OS + Computer Organisation", "Data Structures + Algorithms",
                    "OOPs + C/Java/Python", "SDLC + Web + Emerging Tech + Linux"][(day - LEARN_END).days % 6]
            rec["tasks"].append({"slot": "pm", "id": f"pkrev-{iso}", "t": f"PK revision, {unit}: class Notes PDF + redo the Quiz"})
            rec["tasks"].append({"slot": "pm", "id": f"farev-{iso}", "t": "Financial Awareness: Cards for 3 Banking classes + 2 Govt Scheme parts"})
        else:
            taper = {
             "2026-12-14": "Re-attempt the wrong questions from Mocks 1 and 2",
             "2026-12-15": "Re-attempt the wrong questions from Mocks 3 and 4",
             "2026-12-16": "Re-attempt the wrong questions from Mock 5 + the RRB Scale II General free mock",
             "2026-12-17": "Banking + Govt Scheme Cards, full pass (FA is 40 marks in 15 min)",
             "2026-12-18": "PK Notes skim: one page per unit + Quant formula sheet + CA round-ups (Jul–Oct)",
             "2026-12-19": "Light day: Cards only for 1 hour. Admit card, photo ID, centre route. Sleep by 10:30.",
            }[iso]
            rec["tasks"].append({"slot": "pm", "id": f"taper-{iso}", "t": taper})
    rec["tasks"].append({"slot": "close", "id": f"close-{iso}", "t": "Close: Oliveboard daily CA Quiz (10 min) + write every wrong question in your error log (10 min)"})
    days.append(rec)
    day += dt.timedelta(days=1)

left = {k: len(v) for k, v in queues.items() if v}
skipped = [entry(c) for c in items if c["mode"] == "skip"]
summary = defaultdict(lambda: {"n": 0, "mins": 0, "watch": 0, "notes": 0, "skip": 0, "done": 0, "planned_min": 0})
for c in items:
    s = summary[c["subj"]]
    s["n"] += 1; s["mins"] += c["mins"]; s[c["mode"]] += 1; s["planned_min"] += c["est"]
baseline = {}
for r in days:
    for e in r["am"] + r["pm"]:
        baseline[e["id"]] = r["date"]
def qentry(c):
    e = entry(c)
    if c.get("release"): e["rel"] = c["release"]
    if c["subj"] == "Q": e["cv"] = cv_topic(c["title"])
    return e
def pos(c):
    if c["id"].startswith("b"): return LIB_BY_ID[c["id"][1:]]["idx"]
    return -1 if c["title"] == "How to Crack Quant with this course" else LIB_BY_ID[c["id"]]["idx"]
export_queues = {}
for k, v in INITIAL_QUEUES.items():
    q_ = [qentry(c) for c in v]
    for e in lib:
        if e["st"] == "watched" and e["s"] == k:
            w_ = {x: e[x] for x in ("id", "s", "t", "len", "sp", "w", "pr", "est", "cid", "q") if x in e}
            w_.update({"m": "watch", "watched": 1})
            q_.append(w_)
    q_.sort(key=lambda x: -1 if x["t"] == "How to Crack Quant with this course" else (LIB_BY_ID[x["id"][1:]]["idx"] if x["id"].startswith("b") else LIB_BY_ID[x["id"]]["idx"]))
    export_queues[k] = q_
plan = {"queues": export_queues, "lib": lib,
        "baseline": baseline,
        "tests": {k: [{"id": f"test-{k}", "t": t[0], "est": t[1], "list": t[2][0], "url": t[2][1]} for t in v] for k, v in TESTS.items()},
        "sectionals": [{"t": a, "list": b[0], "url": b[1]} for a, b in PHASE2_SECTIONALS],
        "skipped": [entry(c) for c in items if c["mode"] == "skip"],
        "watched_before": sum(1 for c in items if c["mode"] == "done")}
json.dump(plan, open(OUT.replace(".json", "_plan.json"), "w"), ensure_ascii=False)
json.dump({"days": days, "skipped": skipped, "summary": summary, "bundles": [{"id": b["id"], "s": b["subj"], "t": b["title"], "why": b["why"]} for b in bundle_items]}, open(OUT, "w"), ensure_ascii=False)
print("leftover in queues:", left)
for k, v in summary.items(): print(k, v)
last = {}
for r in days:
    for e in r["am"] + r["pm"]:
        last[e["s"]] = r["date"]
print("last class per subject:", last)
loads = [(r["date"], sum(e["est"] for e in r["pm"]) + sum(t["est"] for t in r["tests"]), sum(e["est"] for e in r["am"])) for r in days]
print("max pm load", max(loads, key=lambda x: x[1]), "max am", max(loads, key=lambda x: x[2]))
print("light pm days (<90 before Nov 29):", [l for l in loads if l[1] < 90 and l[0] <= "2026-11-29"])
