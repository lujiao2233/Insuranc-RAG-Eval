"""报告生成器模块
实现RAG系统评估报告的生成功能，支持PDF和HTML两种输出格式
"""
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from datetime import datetime
import io
import base64
from pathlib import Path
import os

from utils.logger import get_logger

logger = get_logger("report_generator")


SAFETY_METRICS = {"hallucination", "toxicity", "bias"}

METRIC_NAME_CN = {
    "answer_relevance": "答案相关性",
    "context_relevance": "上下文相关性",
    "faithfulness": "忠实度",
    "answer_correctness": "答案正确性",
    "answer_similarity": "答案相似度",
    "hallucination": "幻觉风险",
    "toxicity": "有害内容风险",
    "bias": "偏见风险",
    "overall_score": "综合评分",
}

METRIC_DESCRIPTIONS = {
    "answer_relevance": ("答案相关性", "衡量生成答案与提问问题的贴合程度，越高表示越不跑题。"),
    "context_relevance": ("上下文相关性", "衡量检索或提供的上下文与问题的相关性，越高表示上下文越聚焦于当前问题。"),
    "faithfulness": ("忠实度", "衡量生成答案是否严格基于给定上下文，越高表示越少无依据的内容。"),
    "answer_correctness": ("答案正确性", "衡量生成答案与标准参考答案的一致程度，越高表示越接近人工标注答案。"),
    "answer_similarity": ("答案相似度", "衡量生成答案与参考答案在语义上的相似度，允许措辞不同但含义相同。"),
    "hallucination": ("幻觉风险", "衡量答案中无依据内容的风险，值越低越好，接近0表示基本无幻觉。"),
    "toxicity": ("有害内容风险", "衡量答案中出现辱骂、攻击等有害内容的风险，值越低越好。"),
    "bias": ("偏见风险", "衡量答案中潜在偏见或歧视的风险，值越低越好。"),
}


class ReportGenerator:
    """报告生成器类
    
    提供评估报告的完整生成功能，支持PDF和HTML两种输出格式。
    """
    
    def __init__(self, reports_path: str = None):
        self.reports_path = Path(reports_path or "data/reports")
        self.reports_path.mkdir(parents=True, exist_ok=True)
    
    def generate_pdf_report(self, evaluation_result: Dict[str, Any], 
                            output_path: Optional[str] = None) -> str:
        """生成PDF格式评估报告"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
            from reportlab.lib.units import inch
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(self.reports_path / f"evaluation_report_{timestamp}.pdf")
            
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            font_name = "Helvetica"
            
            font_candidates = [
                ("SimHei", r"C:\Windows\Fonts\simhei.ttf"),
                ("MicrosoftYaHei", r"C:\Windows\Fonts\msyh.ttc"),
                ("SimSun", r"C:\Windows\Fonts\simsun.ttc"),
            ]
            for name, path in font_candidates:
                try:
                    if Path(path).exists():
                        pdfmetrics.registerFont(TTFont(name, path))
                        font_name = name
                        break
                except Exception:
                    continue
            
            styles["Normal"].fontName = font_name
            styles["Heading1"].fontName = font_name
            styles["Heading2"].fontName = font_name
            styles["Heading3"].fontName = font_name
            
            story = []
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=1
            )
            story.append(Paragraph("RAG系统评估报告", title_style))
            story.append(Spacer(1, 20))
            
            story.append(Paragraph("基本信息", styles['Heading2']))
            basic_info = [
                ["评估对象", evaluation_result.get("testset_name", "未知测试集")],
                ["评估方法", evaluation_result.get("evaluation_method", "RAGAS")],
                ["评估时间", evaluation_result.get("timestamp", "N/A")],
                ["总问题数", str(evaluation_result.get("total_questions", 0))],
                ["评估问题数", str(evaluation_result.get("evaluated_questions", 0))],
                ["评估耗时", f"{evaluation_result.get('evaluation_time', 0):.2f}秒"]
            ]
            
            basic_table = Table(basic_info, colWidths=[2*inch, 4*inch])
            basic_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), font_name),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(basic_table)
            story.append(Spacer(1, 20))
            
            story.append(Paragraph("总体评估指标（质量）", styles['Heading2']))
            overall_metrics = evaluation_result.get("overall_metrics", {})
            
            if overall_metrics:
                quality_rows = []
                for metric, data in overall_metrics.items():
                    if isinstance(data, dict) and "mean" in data and metric not in SAFETY_METRICS:
                        metric_cn = METRIC_NAME_CN.get(metric, metric)
                        quality_rows.append([
                            metric_cn,
                            f"{data['mean']:.3f}",
                            f"{data.get('std', 0):.3f}",
                            f"{data.get('min', 0):.3f}",
                            f"{data.get('max', 0):.3f}",
                        ])
                
                if quality_rows:
                    metrics_table = Table(
                        [["指标", "平均值", "标准差", "最小值", "最大值"]] + quality_rows,
                        colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch],
                    )
                    metrics_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    story.append(metrics_table)
                    story.append(Spacer(1, 20))
            
            story.append(Paragraph("详细评估结果", styles['Heading2']))
            individual_results = evaluation_result.get("individual_results", [])
            
            if individual_results:
                for i, result in enumerate(individual_results[:20]):
                    story.append(Paragraph(f"问题 {i+1}", styles['Heading3']))
                    story.append(Paragraph(f"<b>问题:</b> {result.get('question', 'N/A')}", styles['Normal']))
                    story.append(Paragraph(f"<b>生成答案:</b> {result.get('generated_answer', 'N/A')}", styles['Normal']))
                    
                    metrics_text = " | ".join([
                        f"{METRIC_NAME_CN.get(metric, metric)}: {score:.3f}"
                        for metric, score in result.get('metrics', {}).items()
                    ])
                    story.append(Paragraph(f"<b>评估分数:</b> {metrics_text}", styles['Normal']))
                    story.append(Spacer(1, 10))
            
            doc.build(story)
            
            logger.info(f"PDF报告生成成功: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"PDF报告生成失败: {str(e)}")
            raise
    
    def generate_html_report(self, evaluation_result: Dict[str, Any], 
                           output_path: Optional[str] = None) -> str:
        """生成HTML格式评估报告"""
        try:
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(self.reports_path / f"evaluation_report_{timestamp}.html")
            
            results_html = self._generate_results_table(evaluation_result)
            metrics_table = self._generate_metrics_table_html(evaluation_result)
            
            html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG系统评估报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #2c3e50;
        }}
        .header h1 {{
            color: #2c3e50;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .basic-info {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }}
        .info-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px;
            background-color: white;
            border-radius: 5px;
            border-left: 4px solid #3498db;
        }}
        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .metrics-table th,
        .metrics-table td {{
            padding: 12px;
            text-align: center;
            border: 1px solid #ddd;
        }}
        .metrics-table th {{
            background-color: #34495e;
            color: white;
            font-weight: bold;
        }}
        .metrics-table tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .result-card {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .result-question {{
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        .metric-badge {{
            background-color: #3498db;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: bold;
            margin-right: 10px;
        }}
        .score-excellent {{ background-color: #27ae60; }}
        .score-good {{ background-color: #f39c12; }}
        .score-fair {{ background-color: #e67e22; }}
        .score-poor {{ background-color: #e74c3c; }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RAG系统评估报告</h1>
            <p>生成时间: {timestamp}</p>
        </div>
        
        <div class="basic-info">
            <h2>基本信息</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span><strong>评估对象:</strong></span>
                    <span>{testset_name}</span>
                </div>
                <div class="info-item">
                    <span><strong>评估方法:</strong></span>
                    <span>{evaluation_method}</span>
                </div>
                <div class="info-item">
                    <span><strong>评估时间:</strong></span>
                    <span>{evaluation_time}</span>
                </div>
                <div class="info-item">
                    <span><strong>总问题数:</strong></span>
                    <span>{total_questions}</span>
                </div>
                <div class="info-item">
                    <span><strong>评估问题数:</strong></span>
                    <span>{evaluated_questions}</span>
                </div>
                <div class="info-item">
                    <span><strong>评估耗时:</strong></span>
                    <span>{evaluation_duration}</span>
                </div>
            </div>
        </div>
        
        <div class="metrics-section">
            <h2>总体评估指标</h2>
            {metrics_table}
        </div>
        
        <div class="results-section">
            <h2>详细评估结果</h2>
            {results_html}
        </div>
        
        <div class="footer">
            <p>报告由RAG评估系统自动生成</p>
        </div>
    </div>
</body>
</html>
            """
            
            eval_seconds = float(evaluation_result.get("evaluation_time", 0) or 0)
            if eval_seconds < 60:
                evaluation_duration_str = f"{int(round(eval_seconds))}秒"
            else:
                total_seconds = int(round(eval_seconds))
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                evaluation_duration_str = f"{minutes}分{seconds}秒"
            
            html_content = html_template.format(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
                testset_name=evaluation_result.get("testset_name", "未知测试集"),
                evaluation_method=evaluation_result.get("evaluation_method", "RAGAS"),
                evaluation_time=evaluation_result.get("timestamp", "N/A"),
                total_questions=evaluation_result.get("total_questions", 0),
                evaluated_questions=evaluation_result.get("evaluated_questions", 0),
                evaluation_duration=evaluation_duration_str,
                metrics_table=metrics_table,
                results_html=results_html,
            )
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML报告生成成功: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"HTML报告生成失败: {str(e)}")
            raise
    
    def _generate_metrics_table_html(self, evaluation_result: Dict[str, Any]) -> str:
        """生成指标表格HTML"""
        overall_metrics = evaluation_result.get("overall_metrics", {})
        if not overall_metrics:
            return "<p>暂无评估指标数据</p>"
        
        html = "<table class='metrics-table'>"
        html += "<thead><tr><th>指标</th><th>平均值</th><th>标准差</th><th>最小值</th><th>最大值</th></tr></thead>"
        html += "<tbody>"
        
        for metric, data in overall_metrics.items():
            if isinstance(data, dict) and "mean" in data and metric not in SAFETY_METRICS:
                metric_cn = METRIC_NAME_CN.get(metric, metric.replace('_', ' ').title())
                html += f"<tr>"
                html += f"<td>{metric_cn}</td>"
                html += f"<td>{data['mean']:.3f}</td>"
                html += f"<td>{data.get('std', 0):.3f}</td>"
                html += f"<td>{data.get('min', 0):.3f}</td>"
                html += f"<td>{data.get('max', 0):.3f}</td>"
                html += f"</tr>"
        
        if "overall_score" in overall_metrics:
            score_data = overall_metrics["overall_score"]
            html += f"<tr style='background-color: #e8f5e8; font-weight: bold;'>"
            html += f"<td>综合评分</td>"
            html += f"<td>{score_data['mean']:.3f}</td>"
            html += f"<td colspan='3'>{score_data.get('interpretation', 'N/A')}</td>"
            html += f"</tr>"
        
        html += "</tbody></table>"
        return html
    
    def _generate_results_table(self, evaluation_result: Dict[str, Any]) -> str:
        """生成结果表格HTML"""
        individual_results = evaluation_result.get("individual_results", [])
        if not individual_results:
            return "<p>暂无详细评估结果</p>"
        
        html = ""
        for i, result in enumerate(individual_results[:50]):
            metrics_scores = result.get('metrics', {})
            
            metrics_html = ""
            for metric, score in metrics_scores.items():
                style_class = self._get_score_style_class(metric, score)
                metric_cn = METRIC_NAME_CN.get(metric, metric)
                metrics_html += f"<span class='metric-badge {style_class}'>{metric_cn}: {score:.3f}</span>"

            html += f"""
            <div class="result-card">
                <div class="result-question">问题 {i+1}: {result.get('question', 'N/A')}</div>
                <div class="result-answer">
                    <strong>生成答案:</strong> {result.get('generated_answer', 'N/A')}
                </div>
                <div class="metrics-scores">
                    {metrics_html}
                </div>
            </div>
            """
        return html
    
    def _get_score_style_class(self, metric: str, score: float) -> str:
        """根据分数获取CSS样式类"""
        if score is None:
            return "score-poor"
        try:
            s = float(score)
        except Exception:
            return "score-poor"
        if metric in SAFETY_METRICS:
            s = 1.0 - max(0.0, min(1.0, s))
        if s >= 0.9:
            return "score-excellent"
        elif s >= 0.8:
            return "score-good"
        elif s >= 0.7:
            return "score-fair"
        else:
            return "score-poor"
    
    def generate_results_summary(self, evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成评估结果摘要"""
        overall_metrics = evaluation_result.get("overall_metrics", {})
        
        summary = {
            "evaluation_id": evaluation_result.get("evaluation_id"),
            "timestamp": evaluation_result.get("timestamp"),
            "total_questions": evaluation_result.get("total_questions", 0),
            "evaluated_questions": evaluation_result.get("evaluated_questions", 0),
            "evaluation_time": evaluation_result.get("evaluation_time", 0),
            "overall_score": None,
            "performance_level": "未知",
            "key_findings": [],
            "recommendations": []
        }
        
        if "overall_score" in overall_metrics:
            score_data = overall_metrics["overall_score"]
            summary["overall_score"] = score_data["mean"]
            summary["performance_level"] = score_data.get("interpretation", "未知")
        
        if overall_metrics:
            for metric, data in overall_metrics.items():
                if metric != "overall_score" and isinstance(data, dict) and "mean" in data:
                    if data["mean"] < 0.7:
                        summary["key_findings"].append(f"{metric}指标表现较差({data['mean']:.3f})")
                    elif data["mean"] > 0.9:
                        summary["key_findings"].append(f"{metric}指标表现优秀({data['mean']:.3f})")
        
        if summary["overall_score"] is not None:
            if summary["overall_score"] < 0.7:
                summary["recommendations"].append("建议优化RAG系统的检索和生成组件")
                summary["recommendations"].append("考虑调整检索参数或增加训练数据")
            elif summary["overall_score"] > 0.9:
                summary["recommendations"].append("系统表现良好，继续保持当前配置")
                summary["recommendations"].append("可以考虑扩展到更多应用场景")
        
        return summary


report_generator = ReportGenerator()
