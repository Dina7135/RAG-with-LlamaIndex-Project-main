# RAG System for Agentic Coding Documentation

## מטרת הפרויקט

מערכת RAG (Retrieval-Augmented Generation) שמנהלת ומאנדקסת קבצי תיעוד של כלי Agentic Coding (Cursor, Claude Code, Kiro וחבריהם). המערכת מאפשרת לתשאל את התיעוד ולהפיק תובנות על בסיס המידע שהצטבר בו.

## תכונות עיקריות

- **חיפוש סמנטי**: אינדוקס וקטורי עם Cohere Embeddings ו-Pinecone
- **נתונים מובנים**: חילוץ אוטומטי של החלטות, כללים ואזהרות מקבצי Markdown
- **Routing חכם**: בחירה אוטומטית בין חיפוש סמנטי לשליפה מובנת באמצעות LlamaIndex Router
- **Event-Driven Architecture**: Workflow המבוסס על אירועים עם State management
- **ממשק משתמש**: Gradio UI לתשאול נוח

## סטאק טכנולוגי

- **Embeddings**: Cohere (embed-english-v3.0)
- **Vector Database**: Pinecone
- **RAG Framework**: LlamaIndex
- **LLM**: OpenAI (gpt-3.5-turbo) - אופציונלי
- **UI**: Gradio
- **Language**: Python 3.13+

## התקנה

```bash
# שכפל את הריפו
git clone <your-repo-url>
cd RAG

# התקנת תלויות עם uv
uv sync

# הגדרת משתני סביבה
cp .env.example .env
# ערוך את .env והכנס את המפתחות שלך:
# COHERE_API_KEY=your_cohere_key
# PINECONE_API_KEY=your_pinecone_key
# OPENAI_API_KEY=your_openai_key  # אופציונלי
```

## הרצה

### 1. הכנת הנתונים

```bash
# חילוץ נתונים מובנים מקבצי Markdown
uv run extract_data.py
```

זה יצור קובץ `structured_data.json` עם החלטות, כללים ואזהרות שחולצו מהתיקייה `kiro-steering/`.

### 2. הרצת הממשק

```bash
# הרצת ממשק Gradio
uv run app.py
```

הממשק יהיה זמין ב: `http://0.0.0.0:7860`

### 3. הרצה דרך CLI

```bash
# הרצת שאלה בודדת
uv run main.py
```

## דוגמאות לשאלות

### חיפוש מובנה - החלטות

**שאלה**: "תן לי רשימה של כל ההחלטות הטכניות שהתקבלו בפרויקט"

**תשובה צפויה**: רשימה מובנית של כל ההחלטות עם תקצירים ומקורות

### חיפוש מובנה - כללים

**שאלה**: "מה ההנחיה העדכנית לגבי שימוש ב-RTL בממשק?"

**תשובה צפויה**: כללים הקשורים ל-RTL עם פילטר על טקסט המכיל "rtl"

**שאלה**: "אילו כללים יש לגבי אבטחת API?"

**תשובה צפויה**: כללים הקשורים לאבטחה ו-API

### חיפוש מובנה - אזהרות

**שאלה**: "אילו דברים סומנו כ'רגישים' בשבוע האחרון?"

**תשובה צפויה**: אזהרות עם פילטר `observed_after` לפני 7 ימים ופילטר טקסט "רגיש"

**שאלה**: "תן לי את כל האזהרות בחומרה גבוהה"

**תשובה צפויה**: אזהרות עם פילטר `severity="high"`

### חיפוש סמנטי

**שאלה**: "איך כדאי לבנות מנגנון חיפוש פנימי?"

**תשובה צפויה**: חיפוש סמנטי - ה-router מזהה שזו שאלה כללית

**שאלה**: "מה הצבע העיקרי שנבחר לדיזיין של המערכת?"

**תשובה צפויה**: תוצאות חיפוש סמנטי עם מידע על צבעי דיזיין

## מבנה הפרויקט

```
RAG/
├── app.py                    # ממשק Gradio
├── main.py                   # נקודת כניסה CLI
├── semantic_search.py        # מנוע חיפוש סמנטי עם Node Postprocessor
├── data_extraction.py        # חילוץ נתונים מובנים
├── query_router.py           # Router ו-Response Synthesizer
├── workflow.py               # Event-Driven Workflow
├── extract_data.py           # סקריפט לחילוץ נתונים
├── kiro-steering/            # קבצי תיעוד לדוגמה
│   ├── tech.md
│   ├── structure.md
│   ├── product.md
│   ├── security.md
│   └── ui-guidelines.md
├── tests/                    # בדיקות יחידה
│   ├── test_data_extraction.py
│   ├── test_query_router.py
│   ├── test_semantic_search.py
│   └── test_workflow.py
├── .env.example              # דוגמה למשתני סביבה
├── pyproject.toml            # תלויות Python
└── README.md                 # קובץ זה
```

## ארכיטקטורה

### שלב א' - MVP: תשאול סמנטי
1. **Loading**: טעינת קבצי Markdown עם SimpleDirectoryReader
2. **Chunking**: חיתוך ל-chunks עם SentenceSplitter
3. **Embedding**: יצירת embeddings עם Cohere
4. **VectorStoreIndex**: אינדוקס וקטורי
5. **Pinecone**: שמירת וקטורים
6. **Retrieve**: שליפה עם Retriever
7. **Postprocessing**: סינון עם SimilarityPostprocessor
8. **Synthesizing**: יצירת תשובה עם Response Synthesizer

### שלב ב' - Event-Driven Architecture
- **WorkflowEngine**: מנוע מבוסס אירועים
- **WorkflowState**: ניהול מצב
- **WorkflowEvent**: אירועים שמנווטים את הזרימה
- **Validations**: בדיקות תקינות בכל שלב

### שלב ג' - Data Extraction
- **StructuredDataExtractor**: חילוץ נתונים מובנים
- **LlamaIndexRouter**: Routing חכם עם LLMSingleSelector
- **StructuredQueryPlanner**: תכנון שאילתות
- **StructuredDataRetriever**: שליפה עם פילטרים

## בדיקות

```bash
# הרצת כל הבדיקות
.venv\Scripts\python.EXE -m unittest discover tests/ -v

# הרצת בדיקה ספציפית
.venv\Scripts\python.EXE -m unittest tests.test_data_extraction
```

## רכיבי LlamaIndex שבשימוש

- **Node Postprocessor**: SimilarityPostprocessor לסינון תוצאות
- **Response Synthesizer**: get_response_synthesizer ליצירת תשובות
- **Router**: LLMSingleSelector לניתוב חכם
- **QueryEngineTool**: כלי ל-Router

## הערות חשובות

- קבצי ה-md משתנים ומתעדכנים תוך כדי עבודה - בשלב זה התוכן נחשב סטטי
- המערכת תומכת ב-Hebrew ו-English
- ה-Router יכול לעבוד עם או בלי LLM (עם fallback ל-heuristics)
- ה-Response Synthesizer דורש OpenAI API Key לפונקציונליות מלאה

## רישיון

פרויקט זה נוצר לצרכי לימוד והדגמה.
