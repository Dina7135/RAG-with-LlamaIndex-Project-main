import os
from typing import Optional

import gradio as gr

from query_router import answer_question
from netfree_unstrict_ssl import unstrict_ssl
unstrict_ssl()

def run_interface():
    structured_data_file = os.getenv("STRUCTURED_DATA_FILE", "structured_data.json")
    source_dir = os.getenv("SOURCE_DIR", "kiro-steering")

    def answer(question: str, mode: Optional[str] = None) -> str:
        if not question or not question.strip():
            return "אנא הזן שאלה תקינה."

        return answer_question(question, structured_data_file, source_dir)

    with gr.Blocks(title="RAG Project UI") as demo:
        gr.Markdown("# RAG Project\n\nממשק פשוט להרצת חיפוש סמנטי או שליפה ממידע מובנה.")

        with gr.Row():
            question_input = gr.Textbox(label="שאלה", placeholder="כתוב כאן את השאלה שלך...", lines=2)
            run_button = gr.Button("חפש")

        answer_output = gr.Textbox(label="תשובה", lines=10)

        run_button.click(fn=answer, inputs=[question_input], outputs=[answer_output])

        gr.Examples(
            examples=[
                "תן לי רשימה של כל ההחלטות הטכניות שהתקבלו בפרויקט.",
                "מה ההנחיה העדכנית לגבי שימוש ב-RTL בממשק?",
                "אילו דברים סומנו כ'רגישים' בשבוע האחרון?",
            ],
            inputs=[question_input],
        )

        gr.Markdown("---\n`STRUCTURED_DATA_FILE` ניתן לשנות דרך משתני סביבה.")

    demo.launch(server_name="0.0.0.0", share=False)


if __name__ == "__main__":
    run_interface()
