"""
개별 제품 분석 마크다운 보고서들을 1개의 종합 통합 보고서로 병합하는 스크립트.

이 스크립트는 'intimate/report/' 디렉토리 내에 있는 18개 개별 제품 분석 리포트를 읽어들여
목차(TOC)와 함께 구조화된 단일 마크다운 파일 'intimate/report/all_products_analysis_integrated.md'로 생성합니다.
"""

import os

def merge_all_product_reports():
    report_dir = os.path.join("intimate", "report")
    
    # 통합할 개별 제품 분석 파일 목록 (순서 정렬: 기준 제품 -> 경쟁사들)
    product_files = [
        ("★ [기준 타깃] 라엘(Rael) 천연 여성청결제", "target_rael_analysis.md"),
        ("01. 이너시아(INERTIA) 더 퓨어 3X 마이크로바이옴", "inertia_analysis.md"),
        ("02. 질경이(Jilgyungyi) 데일리 에코아 워시 골드", "jilgyungyi_analysis.md"),
        ("03. 클리티(Cleety) 락토 리쥬브네이팅 젤링워시", "cleety_analysis.md"),
        ("04. 뷰티레시피(B.RECIPE) 리틀머메이드 프로바이오틱스 젤", "beautyrecipe_analysis.md"),
        ("05. 아토팜(ATOPALM) 매터니티 케어 마일드 앤 수딩", "atopalm_analysis.md"),
        ("06. 유리아쥬(Uriage) 진피 마일드 젤", "uriage_analysis.md"),
        ("07. 메디온(MEDION) 락토리메디 포밍워시", "medion_analysis.md"),
        ("08. 이너생각(Saengak) 밸런싱 휩드워시", "saengak_analysis.md"),
        ("09. 바솔(BASOL) 이너 밸런싱 포밍 워시", "basol_analysis.md"),
        ("10. 아로마티카(AROMATICA) 퓨어 앤 소프트", "aromatica_analysis.md"),
        ("11. 아로마티카(AROMATICA) 컴포트 모이스처 로즈", "aromatica_rose_analysis.md"),
        ("12. 일리윤(Illiyoon) 세라마이드 더마 페미닌 워시", "illiyoon_analysis.md"),
        ("13. 쏘피(SOFY) 쿨링프레쉬 여성청결제", "sofy_analysis.md"),
        ("14. 디어스킨(Dearskin) 락토 여성청결제", "dearskin_analysis.md"),
        ("15. 해피바스(Happy Bath) 정말 순한 여성청결제 로즈", "happybath_rose_analysis.md"),
        ("16. 해피바스(Happy Bath) 쑥 여성청결제 버블 폼", "happybath_herbal_analysis.md"),
        ("17. 좋은느낌(Good Feel) 더밸런스 바이옴", "oliveyoung_goodfeel_analysis.md")
    ]
    
    merged_lines = []
    
    # 1. 통합 문서 헤더 및 개요
    merged_lines.append("# [여성청결제 카테고리 전체 제품별 상세페이지 분석 통합 보고서]")
    merged_lines.append("> **(기준 제품(라엘) 포함 총 18개 주요 브랜드 전수 상세 분석 단일 통합본)**\n")
    merged_lines.append("- **분석 대상 브랜드 수**: 기준 제품 1개 + 주요 경쟁사 17개 제품 (총 18개 제품)")
    merged_lines.append("- **분석 일자**: 2026-08-30")
    merged_lines.append("- **연계 리포트**: [시장 포지셔닝 맵](market_positioning_map.md) | [종합 비교 매트릭스](competitive_matrix_analysis.md) | [결핍 분석 및 카피 전략](gap_analysis_and_copy_strategy.md) | [최종 종합 마스터 전략](comprehensive_market_comparison.md)\n")
    merged_lines.append("---\n")
    
    # 2. 목차 (Table of Contents) 생성
    merged_lines.append("## 📑 전체 수록 제품 목차 (Table of Contents)\n")
    merged_lines.append("| 번호 | 브랜드 및 제품명 | 핵심 소구 카테고리 | 바로가기 |")
    merged_lines.append("| :---: | :--- | :--- | :---: |")
    
    for idx, (title, filename) in enumerate(product_files):
        anchor_name = f"product-{idx}"
        cat_tag = "기준 제품 (클린뷰티)" if idx == 0 else ("고기능 메디컬/임상" if idx in [1,2,3,4,7,8] else ("더마/장벽/임산부" if idx in [5,6,12] else ("클린/비건/웰니스" if idx in [9,10,11,13,14] else "매스 가성비")))
        merged_lines.append(f"| {idx} | **{title}** | {cat_tag} | [보고서 보기](#{anchor_name}) |")
        
    merged_lines.append("\n---\n")
    
    # 3. 개별 파일 내용 병합
    for idx, (title, filename) in enumerate(product_files):
        file_path = os.path.join(report_dir, filename)
        anchor_name = f"product-{idx}"
        
        if not os.path.exists(file_path):
            print(f"경고: 파일을 찾을 수 없습니다 - {file_path}")
            continue
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        merged_lines.append(f"<div id=\"{anchor_name}\"></div>\n")
        merged_lines.append(f"# [제품 {idx:02d}] {title}\n")
        merged_lines.append(f"> *원본 분석 파일: [`intimate/report/{filename}`]({filename})* | [▲ 목차로 돌아가기](#📑-전체-수록-제품-목차-table-of-contents)\n")
        merged_lines.append(content)
        merged_lines.append("\n\n" + "="*80 + "\n\n")
        
    output_file = os.path.join(report_dir, "all_products_analysis_integrated.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(merged_lines))
        
    print(f"통합 분석 보고서 생성 성공: {output_file}")

if __name__ == "__main__":
    merge_all_product_reports()
