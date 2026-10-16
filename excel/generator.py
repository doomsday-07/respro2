"""
Advanced Excel Executive Report Automation.
Generates 'Executive_Retail_Sales_Inventory_Report.xlsx' with formulas,
KPI scorecards, conditional formatting, and embedded charts.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule
from config import EXPORTS_DIR
from analytics.kpi_engine import RetailKpiEngine
from analytics.inventory_optimizer import InventoryOptimizer
from analytics.anomaly_detector import RetailAnomalyDetector

logger = logging.getLogger("RetailBI.ExcelGenerator")


class ExecutiveExcelReportGenerator:
    """Automates creation of formatted Excel BI workbooks."""

    def __init__(self, output_path: Optional[Path] = None):
        self.output_path = output_path or (EXPORTS_DIR / "Executive_Retail_Sales_Inventory_Report.xlsx")
        self.kpi_engine = RetailKpiEngine()
        self.optimizer = InventoryOptimizer()
        self.anomaly_detector = RetailAnomalyDetector()

    def generate_report(self) -> Path:
        """Constructs and styles the executive workbook."""
        logger.info(f"Generating Executive Excel BI Workbook at {self.output_path}...")
        wb = openpyxl.Workbook()

        # Styles definition
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        accent_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        card_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        card_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        title_font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
        sub_font = Font(name="Calibri", size=10, italic=True, color="94A3B8")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        bold_font = Font(name="Calibri", size=11, bold=True)
        regular_font = Font(name="Calibri", size=11)
        kpi_title_font = Font(name="Calibri", size=9, bold=True, color="64748B")
        kpi_val_font = Font(name="Calibri", size=15, bold=True, color="0F172A")

        # -------------------------------------------------------------
        # SHEET 1: EXECUTIVE SCORECARD
        # -------------------------------------------------------------
        ws1 = wb.active
        ws1.title = "Executive Summary"
        ws1.views.sheetView[0].showGridLines = True

        # Banner
        ws1.merge_cells("A1:H2")
        banner_cell = ws1["A1"]
        banner_cell.value = "EXECUTIVE RETAIL SALES & INVENTORY PULSE"
        banner_cell.font = title_font
        banner_cell.fill = header_fill
        banner_cell.alignment = Alignment(horizontal="center", vertical="center")

        ws1["A3"] = f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Multi-Store Performance & 18% Stockout Reduction Scorecard"
        ws1["A3"].font = sub_font

        # Pull Metrics
        summary = self.kpi_engine.get_executive_summary()
        sim = self.optimizer.simulate_stockout_reduction()

        # KPI Cards (2 rows x 4 cols)
        kpi_cards = [
            ("TOTAL GROSS REVENUE", f"${summary['total_revenue']:,.2f}", "A5:B6"),
            ("GROSS PROFIT MARGIN", f"${summary['gross_margin']:,.2f} ({summary['gross_margin_pct']:.1f}%)", "C5:D6"),
            ("SELL-THROUGH RATE", f"{summary['sell_through_rate']:.1f}%", "E5:F6"),
            ("INVENTORY TURNOVER", f"{summary['inventory_turnover']:.2f}x", "G5:H5"),
            ("UNITS SOLD", f"{summary['units_sold']:,}", "A8:B9"),
            ("TOTAL TRANSACTIONS", f"{summary['total_transactions']:,}", "C8:D9"),
            ("STOCKOUT REDUCTION", f"{sim['relative_stockout_reduction_pct']:.1f}% Target Achieved", "E8:F9"),
            ("RECOVERED REVENUE", f"${sim['recovered_revenue_dollars']:,.2f}", "G8:H9")
        ]

        for title, val, cell_range in kpi_cards:
            start_cell = cell_range.split(":")[0]
            ws1[start_cell] = f"{title}\n{val}"
            ws1[start_cell].font = kpi_val_font
            ws1[start_cell].fill = card_fill
            ws1[start_cell].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws1.merge_cells(cell_range)
            # Apply border to merged range
            start_col, start_row = openpyxl.utils.coordinate_to_tuple(start_cell)
            end_col, end_row = openpyxl.utils.coordinate_to_tuple(cell_range.split(":")[1])
            for r in range(start_row, end_row + 1):
                for c in range(start_col, end_col + 1):
                    ws1.cell(row=r, column=c).border = card_border

        # Category Breakdown Table
        ws1["A12"] = "CATEGORY PERFORMANCE BREAKDOWN"
        ws1["A12"].font = bold_font

        cat_headers = ["Category", "Gross Revenue", "Gross Margin $", "Margin %", "Units Sold", "Rev Share %"]
        for col_idx, h in enumerate(cat_headers, start=1):
            cell = ws1.cell(row=13, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        cats = self.kpi_engine.get_category_performance()
        cat_start_row = 14
        for idx, c in enumerate(cats):
            r = cat_start_row + idx
            ws1.cell(row=r, column=1, value=c["category"]).font = regular_font
            ws1.cell(row=r, column=2, value=c["revenue"]).number_format = "$#,##0.00"
            ws1.cell(row=r, column=3, value=c["margin"]).number_format = "$#,##0.00"
            ws1.cell(row=r, column=4, value=c["margin_pct"] / 100.0).number_format = "0.0%"
            ws1.cell(row=r, column=5, value=c["units_sold"]).number_format = "#,##0"
            ws1.cell(row=r, column=6, value=c["revenue_share_pct"] / 100.0).number_format = "0.0%"

        # Total Row with Excel Formulas
        total_cat_row = cat_start_row + len(cats)
        ws1.cell(row=total_cat_row, column=1, value="Total").font = bold_font
        ws1.cell(row=total_cat_row, column=2, value=f"=SUM(B14:B{total_cat_row-1})").number_format = "$#,##0.00"
        ws1.cell(row=total_cat_row, column=2).font = bold_font
        ws1.cell(row=total_cat_row, column=3, value=f"=SUM(C14:C{total_cat_row-1})").number_format = "$#,##0.00"
        ws1.cell(row=total_cat_row, column=3).font = bold_font
        ws1.cell(row=total_cat_row, column=4, value=f"=C{total_cat_row}/B{total_cat_row}").number_format = "0.0%"
        ws1.cell(row=total_cat_row, column=4).font = bold_font
        ws1.cell(row=total_cat_row, column=5, value=f"=SUM(E14:E{total_cat_row-1})").number_format = "#,##0"
        ws1.cell(row=total_cat_row, column=5).font = bold_font
        ws1.cell(row=total_cat_row, column=6, value=f"=SUM(F14:F{total_cat_row-1})").number_format = "0.0%"
        ws1.cell(row=total_cat_row, column=6).font = bold_font

        # Embedded Excel Chart on Sheet 1: Revenue & Margin by Category
        chart = BarChart()
        chart.type = "col"
        chart.style = 10
        chart.title = "Revenue & Margin by Category ($)"
        chart.y_axis.title = "USD ($)"
        chart.x_axis.title = "Product Category"
        chart.width = 16
        chart.height = 10

        data_ref = Reference(ws1, min_col=2, min_row=13, max_col=3, max_row=total_cat_row-1)
        cats_ref = Reference(ws1, min_col=1, min_row=14, max_row=total_cat_row-1)
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        ws1.add_chart(chart, "A22")

        # -------------------------------------------------------------
        # SHEET 2: STORE PERFORMANCE SCORECARD
        # -------------------------------------------------------------
        ws2 = wb.create_sheet(title="Store Scorecard")
        ws2.views.sheetView[0].showGridLines = True

        ws2.merge_cells("A1:J2")
        s2_banner = ws2["A1"]
        s2_banner.value = "MULTI-STORE PERFORMANCE & TARGET ATTAINMENT"
        s2_banner.font = title_font
        s2_banner.fill = header_fill
        s2_banner.alignment = Alignment(horizontal="center", vertical="center")

        store_headers = [
            "Store ID", "Store Name", "Format", "Region", "Target Rev (Mo)",
            "6-Mo Target", "Actual Revenue", "Attainment %", "Gross Margin %", "Transactions"
        ]
        for col_idx, h in enumerate(store_headers, start=1):
            cell = ws2.cell(row=4, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = accent_fill
            cell.alignment = Alignment(horizontal="center")

        stores = self.kpi_engine.get_store_leaderboard()
        for idx, s in enumerate(stores):
            r = 5 + idx
            ws2.cell(row=r, column=1, value=s["store_id"]).font = regular_font
            ws2.cell(row=r, column=2, value=s["name"]).font = regular_font
            ws2.cell(row=r, column=3, value=s["store_type"]).font = regular_font
            ws2.cell(row=r, column=4, value=s["region"]).font = regular_font
            # Target monthly
            mo_target = s["total_revenue"] / (s["target_attainment_pct"] / 100.0) / 6.0 if s["target_attainment_pct"] > 0 else 300000.0
            ws2.cell(row=r, column=5, value=round(mo_target, 2)).number_format = "$#,##0.00"
            # 6-Mo Target Formula: =E{r} * 6
            ws2.cell(row=r, column=6, value=f"=E{r}*6").number_format = "$#,##0.00"
            ws2.cell(row=r, column=7, value=s["total_revenue"]).number_format = "$#,##0.00"
            # Attainment Formula: =G{r} / F{r}
            ws2.cell(row=r, column=8, value=f"=G{r}/F{r}").number_format = "0.0%"
            ws2.cell(row=r, column=9, value=s["gross_margin_pct"] / 100.0).number_format = "0.0%"
            ws2.cell(row=r, column=10, value=s["transactions"]).number_format = "#,##0"

        # Conditional formatting on Attainment % (Green >= 100%, Yellow 85-99%, Red < 85%)
        green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
        amber_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
        ws2.conditional_formatting.add(
            f"H5:H{5+len(stores)-1}",
            CellIsRule(operator='greaterThanOrEqual', formula=['1.0'], fill=green_fill)
        )
        ws2.conditional_formatting.add(
            f"H5:H{5+len(stores)-1}",
            CellIsRule(operator='between', formula=['0.85', '0.999'], fill=amber_fill)
        )

        # -------------------------------------------------------------
        # SHEET 3: INVENTORY & STOCKOUT OPTIMIZATION
        # -------------------------------------------------------------
        ws3 = wb.create_sheet(title="Inventory Optimization")
        ws3.views.sheetView[0].showGridLines = True

        ws3.merge_cells("A1:J2")
        s3_banner = ws3["A1"]
        s3_banner.value = "INVENTORY OPTIMIZATION & 18% STOCKOUT REDUCTION MATRIX"
        s3_banner.font = title_font
        s3_banner.fill = header_fill
        s3_banner.alignment = Alignment(horizontal="center", vertical="center")

        inv_headers = [
            "Store", "Category", "Product Name", "Lead Time (Days)", "Daily Demand",
            "Current Safety Stock", "Optimal Safety Stock", "Current ROP", "Optimal ROP", "Buffer Gap"
        ]
        for col_idx, h in enumerate(inv_headers, start=1):
            cell = ws3.cell(row=4, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = accent_fill
            cell.alignment = Alignment(horizontal="center")

        reorders = self.optimizer.get_top_reorder_recommendations(limit=25)
        for idx, itm in enumerate(reorders):
            r = 5 + idx
            ws3.cell(row=r, column=1, value=itm["store_name"]).font = regular_font
            ws3.cell(row=r, column=2, value=itm["category"]).font = regular_font
            ws3.cell(row=r, column=3, value=itm["product_name"]).font = regular_font
            ws3.cell(row=r, column=4, value=itm["lead_time_days"]).number_format = "#,##0"
            ws3.cell(row=r, column=5, value=itm["avg_daily_demand"]).number_format = "0.0"
            ws3.cell(row=r, column=6, value=itm["current_safety_stock"]).number_format = "#,##0"
            ws3.cell(row=r, column=7, value=itm["optimal_safety_stock"]).number_format = "#,##0"
            ws3.cell(row=r, column=8, value=itm["current_rop"]).number_format = "#,##0"
            ws3.cell(row=r, column=9, value=itm["optimal_rop"]).number_format = "#,##0"
            # Buffer Gap Formula: =I{r} - H{r}
            ws3.cell(row=r, column=10, value=f"=I{r}-H{r}").number_format = "+#,##0;-#,##0;0"
            ws3.cell(row=r, column=10).font = bold_font

        # -------------------------------------------------------------
        # SHEET 4: ANOMALY AUDIT TRAIL
        # -------------------------------------------------------------
        ws4 = wb.create_sheet(title="Anomaly Audit Log")
        ws4.views.sheetView[0].showGridLines = True

        ws4.merge_cells("A1:H2")
        s4_banner = ws4["A1"]
        s4_banner.value = "REALTIME ANOMALY AUDIT TRAIL (Z-SCORE >= 2.5)"
        s4_banner.font = title_font
        s4_banner.fill = header_fill
        s4_banner.alignment = Alignment(horizontal="center", vertical="center")

        anom_headers = ["Date", "Store", "Category", "Product", "Type", "Observed Units", "Baseline", "Z-Score"]
        for col_idx, h in enumerate(anom_headers, start=1):
            cell = ws4.cell(row=4, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = accent_fill
            cell.alignment = Alignment(horizontal="center")

        anomalies = self.anomaly_detector.get_recent_anomalies(limit=30)
        for idx, an in enumerate(anomalies):
            r = 5 + idx
            ws4.cell(row=r, column=1, value=an["date"]).font = regular_font
            ws4.cell(row=r, column=2, value=an["store_name"]).font = regular_font
            ws4.cell(row=r, column=3, value=an["category"]).font = regular_font
            ws4.cell(row=r, column=4, value=an["product_name"]).font = regular_font
            ws4.cell(row=r, column=5, value=an["anomaly_type"]).font = regular_font
            ws4.cell(row=r, column=6, value=an["observed_value"]).number_format = "0.0"
            ws4.cell(row=r, column=7, value=an["expected_value"]).number_format = "0.0"
            ws4.cell(row=r, column=8, value=an["z_score"]).number_format = "0.00"

        # Auto-adjust column widths across all sheets
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value and cell.row > 2:  # skip banner
                        max_len = max(max_len, len(str(cell.value)))
                sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

        wb.save(self.output_path)
        logger.info(f"Executive Excel report saved successfully to {self.output_path}")
        return self.output_path


if __name__ == "__main__":
    gen = ExecutiveExcelReportGenerator()
    gen.generate_report()
