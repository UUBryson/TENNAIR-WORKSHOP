"""
demo4_president_report.py
=========================
Generates a multi-page PDF institutional summary report for the President's Office.

This script demonstrates how Python can automate an entire reporting pipeline:
  - Load and clean institutional data
  - Calculate key IR metrics (retention, GPA, enrollment)
  - Produce publication-quality charts with matplotlib
  - Assemble everything into a professional PDF with fpdf2

Requirements: pandas, matplotlib, fpdf2
  pip install pandas matplotlib fpdf2

TENNAIR Workshop — Union University | Bryson McNichols
"""

import os
import tempfile
from datetime import date

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — safe for script use
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from fpdf import FPDF, XPos, YPos

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_FILE = os.path.join(os.path.dirname(__file__), "institutional_data.csv")
OUTPUT_PDF = os.path.join(os.path.dirname(__file__), "presidents_report.pdf")

REPORT_TITLE = "Fall 2025 Institutional Summary"
REPORT_SUBTITLE = "Prepared for the President's Office"
INSTITUTION_NAME = "Union University"
REPORT_DATE = date.today().strftime("%B %d, %Y")

# Brand colors — swap these to match your institution's palette
COLOR_PRIMARY = (0, 51, 102)       # Deep navy
COLOR_ACCENT = (180, 140, 0)       # Gold
COLOR_LIGHT_GRAY = (245, 245, 245)
COLOR_TEXT = (40, 40, 40)
COLOR_WHITE = (255, 255, 255)

CHART_DPI = 150
CHART_WIDTH_INCHES = 7.5
CHART_HEIGHT_INCHES = 3.8


def _mpl(color: tuple[int, int, int]) -> tuple[float, float, float]:
    """Convert a 0-255 RGB tuple to 0-1 float tuple for matplotlib."""
    return (color[0] / 255, color[1] / 255, color[2] / 255)


# ---------------------------------------------------------------------------
# Data loading and cleaning
# ---------------------------------------------------------------------------

def load_data(filepath: str) -> pd.DataFrame:
    """Load the institutional CSV and apply standard cleaning.

    Args:
        filepath: Absolute path to institutional_data.csv.

    Returns:
        Cleaned DataFrame with a numeric RetainedNum column (1/0, NaN for blank).
    """
    df = pd.read_csv(filepath)

    required_columns = {
        "StudentID", "Cohort", "Major", "Classification",
        "Gender", "GPA", "EnrollmentStatus", "Retained"
    }
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing expected columns: {missing}")

    # Numeric retention flag — blanks stay NaN so they're excluded from averages
    df["RetainedNum"] = df["Retained"].map({"Yes": 1, "No": 0})

    print(f"  Loaded {len(df):,} student records from {os.path.basename(filepath)}")
    print(f"  Cohorts present: {sorted(df['Cohort'].unique())}")
    print(f"  Records with blank Retained: {df['RetainedNum'].isna().sum()}")

    return df


# ---------------------------------------------------------------------------
# Metric calculations
# ---------------------------------------------------------------------------

def calculate_overall_retention(df: pd.DataFrame) -> float:
    """Return the institution-wide retention rate, excluding blank rows."""
    return df["RetainedNum"].mean()


def calculate_retention_by_cohort(df: pd.DataFrame) -> pd.Series:
    """Return retention rate per cohort year, sorted ascending."""
    return (
        df.groupby("Cohort")["RetainedNum"]
        .mean()
        .sort_index()
    )


def calculate_retention_by_major(df: pd.DataFrame) -> pd.Series:
    """Return retention rate per major, sorted descending."""
    return (
        df.groupby("Major")["RetainedNum"]
        .mean()
        .sort_values(ascending=False)
    )


def calculate_gpa_by_cohort(df: pd.DataFrame) -> pd.Series:
    """Return mean GPA per cohort year, sorted ascending."""
    return df.groupby("Cohort")["GPA"].mean().sort_index()


def calculate_enrollment_by_classification(df: pd.DataFrame) -> pd.Series:
    """Return headcount per classification."""
    order = ["Freshman", "Sophomore", "Junior", "Senior"]
    counts = df["Classification"].value_counts()
    return counts.reindex(order).dropna()


def calculate_gender_distribution(df: pd.DataFrame) -> pd.Series:
    """Return headcount by gender."""
    return df["Gender"].value_counts()


def calculate_enrollment_status(df: pd.DataFrame) -> pd.Series:
    """Return headcount by enrollment status (Full-Time / Part-Time)."""
    return df["EnrollmentStatus"].value_counts()


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------

def _apply_chart_style(ax: plt.Axes) -> None:
    """Apply a consistent, clean style to any axis."""
    ax.set_facecolor("#FAFAFA")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")
    ax.tick_params(colors="#555555", labelsize=9)
    ax.yaxis.label.set_color("#555555")
    ax.xaxis.label.set_color("#555555")
    ax.title.set_color(_mpl(COLOR_TEXT))


def chart_retention_by_cohort(retention_by_cohort: pd.Series) -> str:
    """Render a line chart of retention rate by cohort. Returns temp file path."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH_INCHES, CHART_HEIGHT_INCHES))
    fig.patch.set_facecolor("white")

    years = retention_by_cohort.index.tolist()
    rates = (retention_by_cohort * 100).tolist()

    navy = tuple(c / 255 for c in COLOR_PRIMARY)
    gold = tuple(c / 255 for c in COLOR_ACCENT)

    ax.plot(years, rates, marker="o", linewidth=2.5, color=navy,
            markersize=8, markerfacecolor=gold, markeredgecolor=navy,
            markeredgewidth=1.5, zorder=3)

    for year, rate in zip(years, rates):
        ax.annotate(f"{rate:.1f}%", xy=(year, rate),
                    xytext=(0, 10), textcoords="offset points",
                    ha="center", fontsize=9, color=navy,
                    fontweight="bold")

    ax.set_ylim(0, 105)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.set_xlabel("Cohort Year", fontsize=10)
    ax.set_ylabel("Retention Rate", fontsize=10)
    ax.set_title("Retention Rate by Cohort Year", fontsize=12, fontweight="bold", pad=12)
    ax.set_xticks(years)
    ax.grid(axis="y", linestyle="--", alpha=0.5, color="#DDDDDD")
    _apply_chart_style(ax)

    fig.tight_layout()
    path = _save_temp_chart(fig)
    plt.close(fig)
    return path


def chart_retention_by_major(retention_by_major: pd.Series) -> str:
    """Render a horizontal bar chart of retention rate by major. Returns temp file path."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH_INCHES, CHART_HEIGHT_INCHES))
    fig.patch.set_facecolor("white")

    majors = retention_by_major.index.tolist()
    rates = (retention_by_major * 100).tolist()

    navy = tuple(c / 255 for c in COLOR_PRIMARY)
    gold = tuple(c / 255 for c in COLOR_ACCENT)

    bars = ax.barh(majors, rates, color=navy, edgecolor="white",
                   linewidth=0.5, height=0.6)

    # Highlight top performer in gold
    bars[0].set_color(gold)

    ax.set_xlim(0, 115)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.set_xlabel("Retention Rate", fontsize=10)
    ax.set_title("Retention Rate by Major", fontsize=12, fontweight="bold", pad=12)
    ax.invert_yaxis()

    for bar, rate in zip(bars, rates):
        ax.text(rate + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{rate:.1f}%", va="center", fontsize=8.5, color="#333333")

    ax.grid(axis="x", linestyle="--", alpha=0.5, color="#DDDDDD")
    _apply_chart_style(ax)

    fig.tight_layout()
    path = _save_temp_chart(fig)
    plt.close(fig)
    return path


def chart_gpa_distribution(df: pd.DataFrame) -> str:
    """Render a GPA histogram with a mean reference line. Returns temp file path."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH_INCHES, CHART_HEIGHT_INCHES))
    fig.patch.set_facecolor("white")

    navy = tuple(c / 255 for c in COLOR_PRIMARY)
    gold = tuple(c / 255 for c in COLOR_ACCENT)

    gpas = df["GPA"].dropna()
    ax.hist(gpas, bins=18, color=navy, edgecolor="white",
            linewidth=0.6, alpha=0.85)

    mean_gpa = gpas.mean()
    ax.axvline(mean_gpa, color=gold, linewidth=2, linestyle="--",
               label=f"Mean GPA: {mean_gpa:.2f}")
    ax.legend(fontsize=9, framealpha=0.7)

    ax.set_xlabel("GPA", fontsize=10)
    ax.set_ylabel("Number of Students", fontsize=10)
    ax.set_title("GPA Distribution — All Students", fontsize=12, fontweight="bold", pad=12)
    ax.grid(axis="y", linestyle="--", alpha=0.5, color="#DDDDDD")
    _apply_chart_style(ax)

    fig.tight_layout()
    path = _save_temp_chart(fig)
    plt.close(fig)
    return path


def chart_enrollment_by_classification(enrollment: pd.Series) -> str:
    """Render a bar chart of headcount by classification. Returns temp file path."""
    fig, ax = plt.subplots(figsize=(CHART_WIDTH_INCHES, CHART_HEIGHT_INCHES))
    fig.patch.set_facecolor("white")

    labels = enrollment.index.tolist()
    counts = enrollment.values.tolist()

    navy = tuple(c / 255 for c in COLOR_PRIMARY)
    gold = tuple(c / 255 for c in COLOR_ACCENT)

    bar_colors = [gold if label == "Freshman" else navy for label in labels]
    bars = ax.bar(labels, counts, color=bar_colors, edgecolor="white",
                  linewidth=0.5, width=0.55)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                str(int(count)), ha="center", va="bottom",
                fontsize=10, fontweight="bold", color="#333333")

    ax.set_ylabel("Number of Students", fontsize=10)
    ax.set_title("Enrollment by Classification", fontsize=12, fontweight="bold", pad=12)
    ax.set_ylim(0, max(counts) * 1.2)
    ax.grid(axis="y", linestyle="--", alpha=0.5, color="#DDDDDD")
    _apply_chart_style(ax)

    fig.tight_layout()
    path = _save_temp_chart(fig)
    plt.close(fig)
    return path


def _save_temp_chart(fig: plt.Figure) -> str:
    """Save a matplotlib figure to a temporary PNG file. Returns the file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmp.name, dpi=CHART_DPI, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    tmp.close()
    return tmp.name


# ---------------------------------------------------------------------------
# Narrative generation
# ---------------------------------------------------------------------------

def build_narrative(
    overall_rate: float,
    retention_by_cohort: pd.Series,
    retention_by_major: pd.Series,
    gpa_by_cohort: pd.Series,
    enrollment: pd.Series,
    gender: pd.Series,
    status: pd.Series,
) -> dict[str, str]:
    """Generate auto-written narrative sentences from computed metrics.

    Returns a dict of labeled sentence strings for embedding in the PDF.
    """
    cohorts = retention_by_cohort.index.tolist()
    rates = (retention_by_cohort * 100).tolist()

    # Year-over-year retention change for most recent two cohorts
    if len(cohorts) >= 2:
        delta = rates[-1] - rates[-2]
        direction = "increase" if delta >= 0 else "decrease"
        yoy_sentence = (
            f"The {cohorts[-1]} cohort showed a {abs(delta):.1f}-percentage-point "
            f"{direction} in retention compared to the {cohorts[-2]} cohort "
            f"({rates[-2]:.1f}% vs. {rates[-1]:.1f}%)."
        )
    else:
        yoy_sentence = "Insufficient cohort data for year-over-year comparison."

    top_major = retention_by_major.index[0]
    top_rate = retention_by_major.iloc[0] * 100
    low_major = retention_by_major.index[-1]
    low_rate = retention_by_major.iloc[-1] * 100

    ft_pct = status.get("Full-Time", 0) / status.sum() * 100
    female_pct = gender.get("Female", 0) / gender.sum() * 100
    freshman_count = int(enrollment.get("Freshman", 0))

    return {
        "overall": (
            f"The institution's overall retention rate stands at {overall_rate:.1%}, "
            f"reflecting outcomes across {retention_by_cohort.sum():.0f} tracked student records."
        ),
        "yoy": yoy_sentence,
        "majors": (
            f"{top_major} leads all programs with a {top_rate:.1f}% retention rate. "
            f"{low_major} presents the greatest opportunity for improvement at {low_rate:.1f}%."
        ),
        "gpa": (
            f"Mean GPA has remained between "
            f"{(gpa_by_cohort.min()):.2f} and {(gpa_by_cohort.max()):.2f} "
            f"across cohort years, indicating stable academic performance."
        ),
        "enrollment": (
            f"Freshmen represent the largest classification this term ({freshman_count} students), "
            f"consistent with recent enrollment growth trends."
        ),
        "demographics": (
            f"{ft_pct:.1f}% of enrolled students attend full-time. "
            f"The student body is {female_pct:.1f}% female."
        ),
    }


# ---------------------------------------------------------------------------
# PDF assembly
# ---------------------------------------------------------------------------

class ReportPDF(FPDF):
    """Custom FPDF subclass with branded header and footer."""

    def header(self) -> None:
        """Render page header on every page after the title page."""
        if self.page_no() == 1:
            return
        self.set_fill_color(*COLOR_PRIMARY)
        self.rect(0, 0, self.w, 10, "F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*COLOR_WHITE)
        self.set_xy(10, 2)
        self.cell(0, 6, f"{INSTITUTION_NAME}  |  {REPORT_TITLE}", align="L")
        self.set_xy(-50, 2)
        self.cell(40, 6, REPORT_DATE, align="R")
        self.set_text_color(*COLOR_TEXT)
        self.ln(8)

    def footer(self) -> None:
        """Render page number footer on every page."""
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}  |  Confidential - For Internal Use Only",
                  align="C")
        self.set_text_color(*COLOR_TEXT)


def add_title_page(pdf: ReportPDF) -> None:
    """Build the title page with institution name, report title, and date."""
    pdf.add_page()

    # Full-width navy header band
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.rect(0, 0, pdf.w, 68, "F")

    # Gold accent bar
    pdf.set_fill_color(*COLOR_ACCENT)
    pdf.rect(0, 68, pdf.w, 3, "F")

    # Institution name
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_xy(0, 18)
    pdf.cell(pdf.w, 10, INSTITUTION_NAME.upper(), align="C")

    # Report title
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_xy(0, 32)
    pdf.cell(pdf.w, 14, REPORT_TITLE, align="C")

    # Subtitle
    pdf.set_font("Helvetica", "", 13)
    pdf.set_xy(0, 50)
    pdf.cell(pdf.w, 10, REPORT_SUBTITLE, align="C")

    # Date block below the band
    pdf.set_text_color(*COLOR_TEXT)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_xy(0, 82)
    pdf.cell(pdf.w, 10, f"Report Date: {REPORT_DATE}", align="C")

    # Decorative divider
    pdf.set_draw_color(*COLOR_ACCENT)
    pdf.set_line_width(0.8)
    pdf.line(30, 96, pdf.w - 30, 96)

    # Brief intro paragraph
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.set_xy(25, 104)
    pdf.multi_cell(
        pdf.w - 50, 6,
        "This report was automatically generated from institutional enrollment and "
        "retention data. It is intended to provide a high-level overview of key "
        "performance indicators for executive review. All figures are based on "
        "current data at the time of generation.",
        align="C",
    )

    # Confidentiality notice
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(130, 130, 130)
    pdf.set_xy(0, pdf.h - 30)
    pdf.cell(pdf.w, 8, "CONFIDENTIAL - For Internal Use Only", align="C")


def add_section_header(pdf: ReportPDF, title: str) -> None:
    """Insert a navy section header bar with white title text."""
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 9, f"  {title}", fill=True,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.ln(2)


def add_narrative(pdf: ReportPDF, text: str) -> None:
    """Add a body narrative paragraph with standard formatting."""
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.multi_cell(0, 5.5, text)
    pdf.ln(3)


def add_metric_row(pdf: ReportPDF, label: str, value: str) -> None:
    """Add a single labeled metric line with light background shading."""
    pdf.set_fill_color(*COLOR_LIGHT_GRAY)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(80, 7, f"  {label}", fill=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, value, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(1)


def add_summary_table(
    pdf: ReportPDF,
    retention_by_cohort: pd.Series,
    gpa_by_cohort: pd.Series,
) -> None:
    """Render a formatted summary table of cohort metrics."""
    add_section_header(pdf, "Cohort Summary Table")

    col_widths = [35, 50, 50, 50]
    headers = ["Cohort", "Retention Rate", "Mean GPA", "YoY Retention Change"]

    # Table header row
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_font("Helvetica", "B", 9)
    for header, width in zip(headers, col_widths):
        pdf.cell(width, 8, f"  {header}", fill=True, border=0)
    pdf.ln()

    # Data rows with alternating shading
    pdf.set_font("Helvetica", "", 9)
    cohorts = retention_by_cohort.index.tolist()
    rates = (retention_by_cohort * 100).tolist()
    gpas = gpa_by_cohort.tolist()

    for row_idx, (cohort, rate, gpa) in enumerate(zip(cohorts, rates, gpas)):
        fill = row_idx % 2 == 0
        bg = (240, 244, 248) if fill else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*COLOR_TEXT)

        if row_idx == 0:
            yoy = "--"
        else:
            delta = rate - rates[row_idx - 1]
            sign = "+" if delta >= 0 else ""
            yoy = f"{sign}{delta:.1f} pp"

        row_values = [str(cohort), f"{rate:.1f}%", f"{gpa:.2f}", yoy]
        for value, width in zip(row_values, col_widths):
            pdf.cell(width, 7, f"  {value}", fill=True, border=0)
        pdf.ln()

    pdf.ln(4)


def add_chart_to_pdf(pdf: ReportPDF, image_path: str, caption: str) -> None:
    """Embed a chart image with a caption below it."""
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.image(image_path, x=pdf.l_margin, w=available_width)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Figure: {caption}", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.ln(4)


def build_pdf(
    overall_rate: float,
    retention_by_cohort: pd.Series,
    retention_by_major: pd.Series,
    gpa_by_cohort: pd.Series,
    enrollment: pd.Series,
    gender: pd.Series,
    status: pd.Series,
    narrative: dict[str, str],
    chart_paths: dict[str, str],
) -> None:
    """Assemble and save the full multi-page PDF report."""
    pdf = ReportPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(left=18, top=18, right=18)

    # Page 1: Title
    add_title_page(pdf)

    # Page 2: Executive Summary
    pdf.add_page()
    add_section_header(pdf, "Executive Summary")
    add_narrative(pdf, narrative["overall"])
    add_narrative(pdf, narrative["yoy"])
    add_narrative(pdf, narrative["demographics"])
    pdf.ln(2)

    add_section_header(pdf, "Key Performance Indicators")
    add_metric_row(pdf, "Overall Retention Rate", f"{overall_rate:.1%}")
    add_metric_row(pdf, "Total Students Tracked", str(
        int(retention_by_cohort.count() > 0 and
            sum(retention_by_cohort.notna()))
    ).replace("True", str(len(retention_by_cohort))))
    add_metric_row(pdf, "Mean GPA (All Students)", f"{gpa_by_cohort.mean():.2f}")
    add_metric_row(pdf, "Full-Time Students",
                   f"{status.get('Full-Time', 0)} "
                   f"({status.get('Full-Time', 0) / status.sum():.1%})")
    add_metric_row(pdf, "Part-Time Students",
                   f"{status.get('Part-Time', 0)} "
                   f"({status.get('Part-Time', 0) / status.sum():.1%})")
    add_metric_row(pdf, "Female Students",
                   f"{gender.get('Female', 0)} "
                   f"({gender.get('Female', 0) / gender.sum():.1%})")
    add_metric_row(pdf, "Male Students",
                   f"{gender.get('Male', 0)} "
                   f"({gender.get('Male', 0) / gender.sum():.1%})")
    pdf.ln(4)

    # Add cohort summary table
    add_summary_table(pdf, retention_by_cohort, gpa_by_cohort)

    # Page 3: Retention Analysis
    pdf.add_page()
    add_section_header(pdf, "Retention Analysis")
    add_narrative(pdf, narrative["yoy"])
    add_chart_to_pdf(pdf, chart_paths["retention_cohort"],
                     "Retention Rate by Cohort Year (line chart)")
    pdf.ln(2)
    add_narrative(pdf, narrative["majors"])
    add_chart_to_pdf(pdf, chart_paths["retention_major"],
                     "Retention Rate by Academic Major (horizontal bar chart)")

    # Page 4: Academic Performance and Enrollment
    pdf.add_page()
    add_section_header(pdf, "Academic Performance")
    add_narrative(pdf, narrative["gpa"])
    add_chart_to_pdf(pdf, chart_paths["gpa_distribution"],
                     "GPA Distribution with Mean Reference Line")
    pdf.ln(2)

    add_section_header(pdf, "Enrollment Breakdown")
    add_narrative(pdf, narrative["enrollment"])
    add_chart_to_pdf(pdf, chart_paths["enrollment_classification"],
                     "Headcount by Classification (Freshman through Senior)")

    pdf.output(OUTPUT_PDF)
    print(f"  PDF saved to: {OUTPUT_PDF}")


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup_temp_files(paths: dict[str, str]) -> None:
    """Remove all temporary chart image files."""
    for key, path in paths.items():
        try:
            os.remove(path)
        except OSError as exc:
            print(f"  Warning: could not delete temp file {path}: {exc}")
    print("  Temporary chart files removed.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Orchestrate data loading, metric calculation, charting, and PDF generation."""
    print("\n" + "=" * 60)
    print(f"  {REPORT_TITLE}")
    print(f"  {REPORT_SUBTITLE}")
    print("=" * 60)

    # Step 1: Load data
    print("\n[1/4] Loading data...")
    df = load_data(DATA_FILE)

    # Step 2: Calculate metrics
    print("\n[2/4] Calculating metrics...")
    overall_rate = calculate_overall_retention(df)
    retention_by_cohort = calculate_retention_by_cohort(df)
    retention_by_major = calculate_retention_by_major(df)
    gpa_by_cohort = calculate_gpa_by_cohort(df)
    enrollment = calculate_enrollment_by_classification(df)
    gender = calculate_gender_distribution(df)
    status = calculate_enrollment_status(df)

    print(f"  Overall retention rate: {overall_rate:.1%}")
    print(f"  Cohort retention rates:\n{(retention_by_cohort * 100).round(1).to_string()}")
    print(f"  GPA by cohort:\n{gpa_by_cohort.round(2).to_string()}")

    narrative = build_narrative(
        overall_rate, retention_by_cohort, retention_by_major,
        gpa_by_cohort, enrollment, gender, status
    )

    # Step 3: Generate charts
    print("\n[3/4] Generating charts...")
    chart_paths = {
        "retention_cohort": chart_retention_by_cohort(retention_by_cohort),
        "retention_major": chart_retention_by_major(retention_by_major),
        "gpa_distribution": chart_gpa_distribution(df),
        "enrollment_classification": chart_enrollment_by_classification(enrollment),
    }
    print(f"  {len(chart_paths)} charts rendered.")

    # Step 4: Assemble PDF
    print("\n[4/4] Assembling PDF report...")
    build_pdf(
        overall_rate=overall_rate,
        retention_by_cohort=retention_by_cohort,
        retention_by_major=retention_by_major,
        gpa_by_cohort=gpa_by_cohort,
        enrollment=enrollment,
        gender=gender,
        status=status,
        narrative=narrative,
        chart_paths=chart_paths,
    )

    cleanup_temp_files(chart_paths)

    print("\n" + "=" * 60)
    print("  Report complete.")
    print(f"  Output: {OUTPUT_PDF}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
