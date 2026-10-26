import os

from query_router import answer_question


def main():
    structured_data_file = os.getenv("STRUCTURED_DATA_FILE", "structured_data.json")
    question = os.getenv(
        "USER_QUESTION",
        "מה ההנחיה העדכנית לגבי שימוש ב-RTL בממשק?",
    )

    answer = answer_question(question, structured_data_file)
    print(answer)


if __name__ == "__main__":
    main()
