# Interview Coach Agent

סוכן שעוזר להתכונן לראיונות עבודה בפיתוח תוכנה (טכני, אישי ומוקלט), בנוי פעמיים:

- **`API/`** - על ה-Messages API הגולמי. כל ה-harness נכתב ידנית, קובץ לכל אחריות ב-`API/harness/`.
- **`SDK/`** - על Claude Agent SDK. Claude Code מריץ את ה-harness, והקוד רק מגדיר אותו.

שתי הגרסאות משתמשות באותם כלים ונתונים מ-`shared/`.

## הסוכן

| נושא | מימוש |
|---|---|
| כלים | `get_questions`, `log_practice`, `get_progress`, `save_memory`, ו-`read_job_description` (חיצוני: קורא קובץ מהדיסק) |
| זיכרון | `state/<version>/memory.json` (מפתח -> ערך). נדחף ל-system prompt בתחילת כל סשן |
| קונטקסט | נדחף רק מה שקטן ותמיד רלוונטי (הוראות + זיכרון). בנק השאלות, יומן התרגול וקובץ המשרה נשלפים בכלים |
| טוקנים | פלט כלים קצר (שורה לשאלה, סיכום לנושא), ומדידת טוקנים ועלות לכל תור |

## מבנה

```
shared/      כלים (domain.py), מצב (store.py), system prompt, הרצת תרחיש ובדיקות, report.py
API/         main.py, agent.py, harness/{loop,tools,history,memory,context,compaction,caching,tokens}.py
SDK/         main.py, agent.py, tools.py
tests/       בדיקות offline עם client מדומה
job_descriptions/  קבצי משרה שהכלי החיצוני קורא
scenario.json      7 פניות בשני סשנים + 7 בדיקות pass/fail
results/     api.json, sdk.json
REPORT.md
```

## התקנה (Windows / PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` נוצר עם `pip freeze`, כך שהגרסאות נעולות ושתי הגרסאות רצות על אותן ספריות.

## בדיקות offline (בלי מפתח, בלי עלות)

```powershell
python -m pytest -q
```

## הרצת התרחיש

**API** - צריך מפתח מ-Claude Console, רק כמשתנה סביבה בטרמינל:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python API/main.py --scenario scenario.json --out results/api.json
Remove-Item Env:ANTHROPIC_API_KEY
```

**SDK** - רץ על ה-login של Claude Code. `ANTHROPIC_API_KEY` חייב להיות לא מוגדר:

```powershell
python SDK/main.py --scenario scenario.json --out results/sdk.json
```

**טבלאות לדוח:**

```powershell
python shared/report.py
```

כל ריצה מוחקת את `state/<version>/` ומתחילה ממצב נקי. מודל: `claude-opus-5-5`, effort: `medium`, בשתי הגרסאות.
