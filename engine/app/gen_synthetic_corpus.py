"""Deterministic generator for the two synthetic tenancy-test filings.

T6.5 (two-user isolation) ingested two fake 10-K excerpts, owned by test
users "bruno" and "carla", to prove one tenant cannot retrieve another's
chunks. Those PDFs were built ad hoc, never committed, then deleted — 143
of the 428 points in Qdrant were resting on documents nobody could
reproduce. This script is the fix: it holds the excerpt text as literal
constants and lays it out into a PDF with PyMuPDF (already a pinned
dependency — no new one for a test fixture), so `ingest.py` can rebuild
both documents byte-for-byte-equivalent-in-content from source control
alone.

Content is invented for isolation testing, not drawn from any real
filing — it does not need to be, and must not be mistaken for, a real
company's disclosure.
"""

import argparse
import os

import fitz

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN = 72
FONT = "helv"
FONT_SIZE = 10

DOCS: dict[str, list[str]] = {
    "bruno_10k_excerpt": [
        "BRUNO ROBOTICS, INC.\nForm 10-K Excerpt (Synthetic Test Filing)\n\n"
        "Item 1. Business\n\n"
        "Bruno Robotics, Inc. designs, manufactures, and sells autonomous "
        "warehouse robotics systems for mid-size logistics operators. The "
        "Company was founded in 2014 and is headquartered in Akron, Ohio. "
        "Our principal product line, the Bruno Sorter series, automates "
        "parcel sortation for distribution centers processing between "
        "5,000 and 50,000 packages per day. As of the end of the fiscal "
        "year, the Company employed 1,240 people across three "
        "manufacturing sites and one research campus.",

        "The Company operates in a single reportable segment: Warehouse "
        "Automation Hardware. Revenue is generated primarily through "
        "unit sales of sorter hardware, recognized at the point of "
        "installation acceptance, and through multi-year service "
        "contracts, recognized ratably over the contract term. During "
        "the fiscal year, hardware sales represented approximately 68% "
        "of total revenue and service contracts represented "
        "approximately 32%. The Company's ten largest customers "
        "accounted for 41% of total revenue, and no single customer "
        "accounted for more than 9% of total revenue.",

        "Item 1A. Risk Factors\n\n"
        "Our business depends on a small number of component suppliers "
        "for precision servo motors and depth-sensing cameras. A "
        "sustained disruption at any of these suppliers could delay "
        "shipments and harm customer relationships. We compete against "
        "larger, better-capitalized robotics manufacturers who may be "
        "able to offer lower prices or faster delivery. Our warranty "
        "reserves are based on historical failure rates that may not "
        "predict future failure rates accurately, particularly for "
        "product configurations introduced in the last twelve months.",

        "We are also subject to risks common to hardware manufacturers "
        "operating internationally, including tariff changes affecting "
        "imported subcomponents, currency translation exposure on "
        "contracts denominated in non-U.S. dollars, and the possibility "
        "that a customer's warehouse construction delays could push "
        "installation, and therefore revenue recognition, into a later "
        "fiscal period than originally planned.",

        "Item 7. Management's Discussion and Analysis\n\n"
        "Total revenue for the fiscal year was $184.3 million, an "
        "increase of 11.6% from $165.2 million in the prior fiscal "
        "year. The increase was driven primarily by a 14% increase in "
        "sorter units shipped, partially offset by a decline in average "
        "selling price per unit as the Company introduced a lower-cost "
        "configuration aimed at smaller distribution centers. Service "
        "contract revenue grew 9.8% year over year as the installed "
        "base of active sorters expanded from 612 to 701 units.",

        "Cost of revenue for the fiscal year was $121.7 million, "
        "compared to $109.4 million in the prior year, representing "
        "gross margin of 34.0% versus 33.8% in the prior year. The "
        "modest margin improvement reflects lower per-unit input costs "
        "from a renegotiated servo motor supply agreement, partially "
        "offset by increased freight costs. Operating expenses, "
        "consisting of research and development, sales and marketing, "
        "and general and administrative expense, totaled $48.9 million, "
        "compared to $44.1 million in the prior year.",

        "As of fiscal year end, the Company held $37.2 million in cash "
        "and cash equivalents and $12.5 million in short-term "
        "investments, for total liquidity of $49.7 million. The Company "
        "generated $22.4 million in cash from operating activities "
        "during the fiscal year, used $9.1 million in investing "
        "activities primarily for manufacturing equipment, and used "
        "$3.8 million in financing activities for scheduled term-loan "
        "principal payments. Management believes existing liquidity and "
        "cash generated from operations will be sufficient to fund "
        "operations for at least the next twelve months.",

        "Item 8. Financial Statements\n\n"
        "Consolidated Balance Sheet (in thousands): Total current "
        "assets were $98,412, consisting of cash and cash equivalents "
        "of $37,200, short-term investments of $12,500, accounts "
        "receivable, net, of $31,904, and inventory of $16,808. "
        "Property and equipment, net, was $54,220. Total assets were "
        "$168,930. Total current liabilities were $42,115, consisting "
        "of accounts payable of $18,340, accrued liabilities of "
        "$14,275, and the current portion of long-term debt of $9,500. "
        "Long-term debt, net of current portion, was $31,200. Total "
        "stockholders' equity was $95,615.",

        "Consolidated Statement of Operations (in thousands): Revenue "
        "of $184,300; cost of revenue of $121,700; gross profit of "
        "$62,600; research and development expense of $21,450; sales "
        "and marketing expense of $16,220; general and administrative "
        "expense of $11,230; total operating expenses of $48,900; "
        "operating income of $13,700; interest expense, net, of "
        "$1,850; income before income taxes of $11,850; provision for "
        "income taxes of $2,607; net income of $9,243.",

        "Notes to Financial Statements - Commitments and Contingencies\n\n"
        "The Company leases its Akron headquarters and two of its three "
        "manufacturing facilities under operating leases expiring "
        "between 2028 and 2033. Total future minimum lease payments "
        "under these agreements were $18.6 million as of fiscal year "
        "end. The Company is not currently a party to any legal "
        "proceeding that management believes would, individually or in "
        "the aggregate, have a material adverse effect on its financial "
        "condition or results of operations.",
    ],
    "carla_10k_excerpt": [
        "CARLA TEXTILE HOLDINGS, INC.\nForm 10-K Excerpt (Synthetic Test Filing)\n\n"
        "Item 1. Business\n\n"
        "Carla Textile Holdings, Inc. designs and manufactures "
        "performance outdoor fabrics sold to apparel and gear brands "
        "under private-label and licensed-brand arrangements. The "
        "Company was founded in 2009 and is headquartered in "
        "Greenville, South Carolina, with weaving and finishing "
        "operations in two domestic mills. As of fiscal year end, the "
        "Company employed 860 people.",

        "The Company operates in a single reportable segment: "
        "Technical Fabrics. Revenue is recognized upon shipment of "
        "finished fabric rolls to the customer, which corresponds to "
        "the point at which control transfers under the Company's "
        "shipping terms. During the fiscal year, the Company's five "
        "largest customers accounted for 57% of total revenue, and one "
        "customer, a national outdoor apparel brand, accounted for 19% "
        "of total revenue.",

        "Item 1A. Risk Factors\n\n"
        "Raw material costs, particularly for recycled polyester yarn "
        "and PFAS-free durable water repellent treatments, have been "
        "volatile and may continue to be volatile due to global "
        "petrochemical pricing and evolving environmental regulation. "
        "The Company's customer base is concentrated, and the loss of "
        "any of its largest customers could materially reduce revenue. "
        "The Company has completed its transition away from legacy "
        "fluorinated water-repellent chemistry ahead of new state-level "
        "restrictions, but replacement treatments may perform "
        "differently across fabric weights and could affect customer "
        "acceptance.",

        "Item 7. Management's Discussion and Analysis\n\n"
        "Total revenue for the fiscal year was $96.8 million, a "
        "decrease of 4.2% from $101.1 million in the prior fiscal "
        "year. The decrease was primarily attributable to lower unit "
        "volume from the Company's largest customer as that customer "
        "worked down excess finished-goods inventory carried over from "
        "the prior year, partially offset by a 6% increase in average "
        "selling price per yard reflecting a shift in mix toward "
        "higher-performance laminated fabrics.",

        "Cost of revenue for the fiscal year was $71.6 million, "
        "compared to $73.4 million in the prior year, representing "
        "gross margin of 26.0% versus 27.4% in the prior year. The "
        "margin decline was driven by higher input costs for "
        "PFAS-free durable water repellent chemistry, partially offset "
        "by fixed-cost absorption benefits from a mill efficiency "
        "program completed early in the fiscal year. Operating "
        "expenses totaled $19.4 million, compared to $18.9 million in "
        "the prior year.",

        "As of fiscal year end, the Company held $8.9 million in cash "
        "and cash equivalents. The Company generated $6.3 million in "
        "cash from operating activities during the fiscal year, used "
        "$4.1 million in investing activities primarily for finishing "
        "line upgrades related to the water-repellent chemistry "
        "transition, and used $1.6 million in financing activities. "
        "The Company maintains a $15.0 million revolving credit "
        "facility, of which $3.5 million was drawn as of fiscal year "
        "end.",

        "Item 8. Financial Statements\n\n"
        "Consolidated Balance Sheet (in thousands): Total current "
        "assets were $41,206, consisting of cash and cash equivalents "
        "of $8,900, accounts receivable, net, of $14,320, and "
        "inventory of $16,940. Property and equipment, net, was "
        "$27,650. Total assets were $71,980. Total current liabilities "
        "were $19,415, consisting of accounts payable of $11,280 and "
        "accrued liabilities of $8,135. Long-term debt was $3,500. "
        "Total stockholders' equity was $47,940.",

        "Consolidated Statement of Operations (in thousands): Revenue "
        "of $96,800; cost of revenue of $71,600; gross profit of "
        "$25,200; research and development expense of $3,150; selling "
        "and marketing expense of $8,920; general and administrative "
        "expense of $7,330; total operating expenses of $19,400; "
        "operating income of $5,800; interest expense, net, of $410; "
        "income before income taxes of $5,390; provision for income "
        "taxes of $1,186; net income of $4,204.",

        "Notes to Financial Statements - Commitments and Contingencies\n\n"
        "The Company leases certain warehouse and distribution space "
        "under operating leases expiring between 2027 and 2030. Total "
        "future minimum lease payments under these agreements were "
        "$4.8 million as of fiscal year end. The Company is not "
        "currently a party to any legal proceeding that management "
        "believes would, individually or in the aggregate, have a "
        "material adverse effect on its financial condition or "
        "results of operations.",
    ],
}


def render_pdf(paragraphs: list[str], out_path: str) -> int:
    doc = fitz.open()
    doc.set_metadata({})
    rect = fitz.Rect(MARGIN, MARGIN, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN)
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page_count = 1
    for para in paragraphs:
        remaining = para
        while remaining:
            overflow = page.insert_textbox(
                rect, remaining, fontsize=FONT_SIZE, fontname=FONT
            )
            if overflow >= 0:
                remaining = ""
            else:
                page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
                page_count += 1
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page_count += 1
    doc.delete_page(len(doc) - 1)
    page_count -= 1
    doc.save(out_path, deflate=True, garbage=4)
    doc.close()
    return page_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data/corpus/synthetic")
    parser.add_argument(
        "doc_ids",
        nargs="*",
        help="Which synthetic doc(s) to render; default is both.",
    )
    args = parser.parse_args()
    doc_ids = args.doc_ids or list(DOCS.keys())
    for doc_id in doc_ids:
        if doc_id not in DOCS:
            parser.error(f"unknown doc_id {doc_id!r}; choose from {list(DOCS.keys())}")

    os.makedirs(args.out_dir, exist_ok=True)
    for doc_id in doc_ids:
        out_path = os.path.join(args.out_dir, f"{doc_id}.pdf")
        pages = render_pdf(DOCS[doc_id], out_path)
        print(f"Wrote {out_path} ({pages} pages).")


if __name__ == "__main__":
    main()
