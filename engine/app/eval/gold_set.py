# A gold row may carry "operand_keys": the literal values a derived
# answer_key is computed from, when the computed result itself is not
# expected to appear verbatim anywhere in the source document. Retrieval
# can only be held responsible for surfacing the operands it was built
# from, not for arithmetic no chunk performs. Any eval script scoring
# retrieval by literal-value presence should check operand_keys (if
# present) instead of answer_key — this applies to any row that declares
# it, not only the one row that does today.
GOLD_SET = [
    {"question": "What were Apple's total net sales for fiscal 2025?", "answer_key": "416,161"},
    {"question": "What was Apple's cost of sales in fiscal 2025?", "answer_key": "220,960"},
    {"question": "What was Apple's net income for fiscal 2025?", "answer_key": "112,010"},
    {"question": "How much did Apple spend on research and development in fiscal 2025?", "answer_key": "34,550"},
    {"question": "What was Apple's diluted earnings per share in fiscal 2025?", "answer_key": "7.46"},
    {"question": "How many diluted shares did Apple use to compute earnings per share in fiscal 2025?", "answer_key": "15,004,697"},
    {"question": "What were Apple's total assets as of the end of fiscal 2025?", "answer_key": "359,241"},
    {"question": "What was Apple's operating income for fiscal 2025?", "answer_key": "133,050"},
    {"question": "What was the total of Apple's cash, cash equivalents, and marketable securities at the end of fiscal 2025?", "answer_key": "132.4"},
    {"question": "In the five-year stock performance graph, what was the ending value of a $100 investment in Apple common stock as of September 2025?", "answer_key": "234"},
    {"question": "What base amount was assumed invested in the stock performance comparison graph as of September 2020?", "answer_key": "100"},
    {
        "question": "How much larger was Apple's total net sales than its research and development spend in fiscal 2025?",
        "answer_key": "381,611",
        "operand_keys": ["416,161", "34,550"],
    },
    {"question": "By what date must Apple settle its State Aid Decision obligation using restricted cash held in escrow?", "answer_key": "UNANSWERABLE"},
    {"question": "What does Apple forecast its total net sales will be for fiscal 2026?", "answer_key": "UNANSWERABLE"},
    {"question": "Will Apple's share price exceed $300 by the end of 2026?", "answer_key": "UNANSWERABLE"},
]