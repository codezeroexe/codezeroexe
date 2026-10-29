"""Render fastfetch.svg: colored ASCII logo + live GitHub stats. Stdlib only."""
import json, os, urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape as _esc

USER = "codezeroexe"
PINNED = [  # name, blurb (edit when you change pins on GitHub)
    ("Ultron", "voice assistant for Mac"),
    ("rabbithole", "AI graph explorer"),
    ("levels", "Claude Code skills"),
    ("portfolio", "Next.js + shadcn/ui site"),
]

QUERY = """query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false,
                  orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        name pushedAt stargazerCount forkCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
  }
}"""


def escape(s):  # nbsp: SVG renderers collapse normal spaces
    return _esc(s).replace(" ", " ")


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"},
    )
    data = json.load(urllib.request.urlopen(req))
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def ago(ts):
    d = (datetime.now(timezone.utc) - parse(ts)).days
    return "today" if d == 0 else f"{d} day{'s' * (d != 1)} ago"


def streaks(cal):
    """(current, longest) runs of days with >=1 contribution. Today may still be empty."""
    days = {date.fromisoformat(d["date"]): d["contributionCount"]
            for w in cal["weeks"] for d in w["contributionDays"]}
    longest = run = 0
    for day in sorted(days):
        run = run + 1 if days[day] else 0
        longest = max(longest, run)
    today = max(days)
    day = today if days[today] else today - timedelta(days=1)
    current = 0
    while days.get(day):
        current, day = current + 1, day - timedelta(days=1)
    return current, longest


def columns(u):
    repos = u["repositories"]["nodes"]
    c = u["contributionsCollection"]
    cal = c["contributionCalendar"]
    langs = Counter()
    for r in repos:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] += e["size"]
    total = sum(langs.values()) or 1
    top = max(repos, key=lambda r: r["stargazerCount"])
    cur, best = streaks(cal)
    days = (datetime.now(timezone.utc) - parse(u["createdAt"])).days

    # (label, value). "@title" = accent heading, None = plain text.
    left = [
        ("@title", f"{USER}@github"),
        (None, "-" * (len(USER) + 7)),
        ("OS", "Human, AI/ML edition"),
        ("Host", "MacBook Air (M4)"),
        ("Kernel", "Python 3"),
        ("Uptime", f"{days // 365} years, {days % 365 // 30} months"),
        ("Shell", "zsh"),
        ("DE", "macOS 27"),
        ("Terminal", "Ghostty"),
        ("Agents", "Claude Code, Pi, OpenCode, Goose"),
        ("CPU", "Brain (1 core) @ 3am boost"),
        ("GPU", "Apple M4 + Claude + Figma, overclocked"),
        ("Memory", f"{u['repositories']['totalCount']} repos, 2 brain cells"),
        ("Packages", "Swift, Kotlin, Python, Java"),
        ("Displays", "Android, macOS, Windows, Web"),
        ("Battery", "3% (espresso on the way)"),
        ("Network", "srhxri.runs-on.dev"),
    ]
    right = [
        ("@title", "GitHub stats"),
        (None, "------------"),
        ("Repos", f"{u['repositories']['totalCount']} public"),
        ("Stars", f"{sum(r['stargazerCount'] for r in repos)} earned"),
        ("Forks", str(sum(r["forkCount"] for r in repos))),
        ("Followers", str(u["followers"]["totalCount"])),
        ("Commits", f"{c['totalCommitContributions']} this year"),
        ("PRs", str(c["totalPullRequestContributions"])),
        ("Issues", str(c["totalIssueContributions"])),
        ("Activity", f"{cal['totalContributions']} in the last year"),
        ("Streak", f"{cur} days (best {best})"),
        ("Top repo", f"{top['name']} ({top['stargazerCount']} stars)"),
        ("Last push", f"{repos[0]['name']}, {ago(repos[0]['pushedAt'])}"),
        ("Top langs", ", ".join(f"{n} {s * 100 // total}%" for n, s in langs.most_common(3))),
        (None, ""),
        ("@title", "Pinned"),
        *[(None, f"  {n:<11} {d}") for n, d in PINNED],
    ]
    return left, right


BG, FG, ACCENT, DIM = "#0d1117", "#c9d1d9", "#e3b341", "#6e7681"
PALETTE = ["#484f58", "#ff7b72", "#3fb950", "#d29922", "#58a6ff", "#bc8cff", "#39c5cf", "#f0f6fc"]
CW, LH, PAD, FS = 9.6, 18, 28, 14  # char width (widest common mono), line height, padding, font size
COL = 46  # chars per info column


def logo_svg(logo, x0, y0, k):
    """k scales the logo font, so a high-res logo fits the card width."""
    out = []
    for y, row in enumerate(logo):  # one tspan per same-color run; blanks join the current run
        spans, cur, buf = [], None, ""
        for ch, col in row:
            col = cur if ch == " " else col
            if col != cur and buf:
                spans.append(f'<tspan fill="{cur or FG}">{escape(buf)}</tspan>')
                buf = ""
            cur, buf = col, buf + ch
        spans.append(f'<tspan fill="{cur or FG}">{escape(buf.rstrip())}</tspan>')
        out.append(f'<text x="{x0}" y="{y0 + y * LH * k:.1f}" font-size="{FS * k:.2f}">{"".join(spans)}</text>')
    return out


def info_svg(lines, x0, y0):
    out = []
    for i, (label, value) in enumerate(lines):
        y = y0 + i * LH
        if label == "@title":
            out.append(f'<text x="{x0}" y="{y}" fill="{ACCENT}" font-weight="bold">{escape(value)}</text>')
        elif label:
            out.append(f'<text x="{x0}" y="{y}"><tspan fill="{ACCENT}" font-weight="bold">{label}</tspan>: {escape(value)}</text>')
        else:
            out.append(f'<text x="{x0}" y="{y}">{escape(value)}</text>')
    return out


def render(logo, left, right):
    width = PAD * 2 + (COL * 2 + 4) * CW
    k = min(1, (COL * 2 + 4) / len(logo[0]))
    lx = PAD + (width - PAD * 2 - len(logo[0]) * CW * k) / 2  # center logo
    out = [f'<text x="{PAD}" y="{PAD + FS}" fill="{DIM}">{escape("$ fastfetch --logo hari.png")}</text>']
    top = PAD + FS + LH * 2
    out += logo_svg(logo, lx, top, k)
    y = top + len(logo) * LH * k + LH * 2
    out += info_svg(left, PAD, y)
    out += info_svg(right, PAD + (COL + 4) * CW, y)
    y += (max(len(left), len(right)) + 1) * LH
    out += [f'<rect x="{PAD + k * 3 * CW}" y="{y - FS + 1}" width="{3 * CW}" height="{LH - 2}" fill="{c}"/>'
            for k, c in enumerate(PALETTE)]
    stamp = "updated " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out.append(f'<text x="{width - PAD}" y="{y}" fill="{DIM}" text-anchor="end">{escape(stamp)}</text>')
    height = y + PAD
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">'
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>'
        f'<g font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" font-size="{FS}" fill="{FG}">'
        + "".join(out) + "</g></svg>"
    )


if __name__ == "__main__":
    logo = json.load(open("logo.json"))
    open("fastfetch.svg", "w").write(render(logo, *columns(fetch())))
