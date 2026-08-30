// 이너시아 생리대 서브라인 비교 분석 데이터
// 출처: 올리브영 + 쿠팡 크롤링 (2026-08-27)
window.INERTIA_SUBLINES = [
  {
    subline: '더 프리즘',
    summary: '이너시아의 시그니처 라인. 카이스트 여성 과학자가 개발한 라보셀 흡수체 + 100% 유기농 순면. 중형/대형은 8개입(올리브영)·10개입(쿠팡)으로 판매.',
    channels: ['올리브영', '쿠팡'],
    rating: 4.8,
    reviews: 12021,
    priceRange: '7,700~19,390원',
    sizes: ['중형', '대형', '라이너', '입는오버나이트'],
    rank: 36,
    products: [
      { size: '중형', name: '더 프리즘 유기농 생리대 중형 8개입', price: '7,700원', rating: 4.8, reviews: 12021, channel: '올리브영', url: 'https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000187776' },
      { size: '대형', name: '더 프리즘 유기농 생리대 대형 8개입', price: '7,700원', rating: 4.8, reviews: 12021, channel: '올리브영', url: 'https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000187776' },
      { size: '대형', name: '더 프리즘 생리대 대형 10개입', price: '9,800원', rating: 4.8, reviews: 3627, channel: '쿠팡', url: 'https://www.coupang.com/vp/products/7295333975' },
      { size: '라이너', name: '더 프리즘 팬티라이너 롱 18개입', price: '8,900원', rating: 4.8, reviews: 2048, channel: '쿠팡', url: 'https://www.coupang.com/vp/products/7303692442' },
      { size: '입는오버나이트', name: '더 프리즘 입는오버나이트 중형 4개입', price: '9,900원', rating: 4.8, reviews: 1591, channel: '올리브영', url: 'https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000195421' },
      { size: '입는오버나이트', name: '더 프리즘 입는오버나이트 대형 8개입', price: '19,390원', rating: 4.8, reviews: 5634, channel: '쿠팡', url: 'https://www.coupang.com/vp/products/7887232701' },
    ]
  },
  {
    subline: '더 퍼펙션',
    summary: '흡수력 강화 라인. 셀룰로오스 미세섬유 천연 흡수체 + 고분자 흡수체(SAP) 배제. 중형 14개입·대형 12개입. 쿠팡 리뷰 1.3만 건으로 이너시아 내 최다.',
    channels: ['올리브영', '쿠팡'],
    rating: 4.8,
    reviews: 13147,
    priceRange: '9,500원',
    sizes: ['중형', '대형'],
    rank: 34,
    products: [
      { size: '중형', name: '더 퍼펙션 생리대 중형 14개입', price: '9,500원', rating: 4.8, reviews: 13147, channel: '쿠팡', url: 'https://www.coupang.com/vp/products/8106839172' },
      { size: '대형', name: '더 퍼펙션 생리대 대형 12개입', price: '9,500원', rating: 4.8, reviews: 13147, channel: '쿠팡', url: 'https://www.coupang.com/vp/products/8106839172' },
      { size: '중형', name: '더 퍼펙션 생리대 중형 14개입', price: '9,800원', rating: 4.8, reviews: 1290, channel: '올리브영', url: 'https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000211867' },
    ]
  },
  {
    subline: '더 쿨',
    summary: '즉각 쿨링 라인. 8월 올영픽 선정. 올리브영 단독 입점으로 커버리지 점수가 낮아 순위가 낮음. 입는오버나이트는 평점 4.9.',
    channels: ['올리브영'],
    rating: 4.7,
    reviews: 575,
    priceRange: '7,800~9,500원',
    sizes: ['중형', '대형', '입는오버나이트'],
    rank: 63,
    products: [
      { size: '중형', name: '더 쿨 유기농 생리대 중형', price: '7,800원', rating: 4.7, reviews: 575, channel: '올리브영', url: 'https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000257283' },
      { size: '대형', name: '더 쿨 유기농 생리대 대형', price: '7,800원', rating: 4.7, reviews: 575, channel: '올리브영', url: 'https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000257283' },
      { size: '입는오버나이트', name: '더 쿨 입는오버나이트 4개입', price: '9,500원', rating: 4.9, reviews: 61, channel: '올리브영', url: 'https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000260492' },
    ]
  },
];

window.renderInertiaSection = function() {
  var el = document.getElementById('inertiaContent');
  if (!el) return;
  var subs = window.INERTIA_SUBLINES || [];
  var fmt = function(n) { return n ? n.toLocaleString() : 'n.a.'; };
  var colorBy = function(ch) {
    if (ch.length >= 2) return 'var(--color-accent)';
    return 'var(--color-info)';
  };
  var summaryHtml = '<div class="card" style="margin-top:var(--space-5)"><div class="card-body" style="padding:var(--space-6)">' +
    '<h3 style="margin-bottom:var(--space-3)">이너시아 서브라인 비교 요약</h3>' +
    '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:var(--space-4)">' +
    subs.map(function(s) {
      var covLabel = s.channels.length >= 2 ? '2채널 (커버리지 100)' : '1채널 (커버리지 60)';
      return '<div style="background:var(--color-surface-2);border-radius:var(--radius-md);padding:var(--space-4);border-top:3px solid ' + colorBy(s.channels) + '">' +
        '<div style="font-weight:600;margin-bottom:var(--space-2)">' + s.subline + '</div>' +
        '<div style="font-size:1.3rem;font-weight:700;color:var(--color-gold)">' + s.rank + '위</div>' +
        '<div class="kpi-muted">평점 ' + s.rating + ' · 리뷰 ' + fmt(s.reviews) + '건</div>' +
        '<div class="kpi-muted">' + covLabel + ' · ' + s.channels.join('/') + '</div>' +
        '<div class="kpi-muted">' + s.priceRange + '</div>' +
        '<div class="rael-sizes">' + s.sizes.map(function(z) { return '<span>' + z + '</span>'; }).join('') + '</div>' +
        '</div>';
    }).join('') +
    '</div></div></div>';

  var detailHtml = subs.map(function(s) {
    var rows = s.products.map(function(p) {
      return '<tr><td>' + p.size + '</td><td>' + p.name + '</td>' +
        '<td style="text-align:right">' + p.price + '</td>' +
        '<td style="text-align:right">' + p.rating + '</td>' +
        '<td style="text-align:right">' + fmt(p.reviews) + '</td>' +
        '<td>' + p.channel + '</td>' +
        '<td><a href="' + p.url + '" target="_blank" rel="noopener" style="color:var(--color-info)">보기</a></td></tr>';
    }).join('');
    return '<div style="margin-top:var(--space-5)">' +
      '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:var(--space-2)">' +
      '<h4 style="margin:0">' + s.subline + ' (' + s.rank + '위)</h4>' +
      '<span class="kpi-muted">' + s.priceRange + ' · ' + s.channels.join('/') + ' · ' + s.products.length + '개 제품</span>' +
      '</div>' +
      '<p style="font-size:0.85rem;color:var(--color-text-muted);margin:0 0 var(--space-3)">' + s.summary + '</p>' +
      '<div class="table-scroll"><table class="table compact"><thead><tr>' +
      '<th>사이즈</th><th>제품명</th><th style="text-align:right">가격</th><th style="text-align:right">평점</th><th style="text-align:right">리뷰수</th><th>채널</th><th></th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table></div></div>';
  }).join('');

  var insightHtml = '<div style="margin-top:var(--space-6);padding:var(--space-5);background:var(--color-surface-2);border-radius:var(--radius-md);border-left:3px solid var(--color-accent)">' +
    '<h4 style="margin-bottom:var(--space-3)">이너시아 vs 라엘 순위 분석</h4>' +
    '<ul style="margin:0;padding-left:var(--space-5);font-size:0.88rem;line-height:1.7;color:var(--color-text-muted)">' +
    '<li><strong>이너시아 순위:</strong> 더 퍼펙션 <strong>34위</strong>(점수 41.4) · 더 프리즘 <strong>36위</strong>(41.2) · 더 쿨 <strong>63위</strong>(34.3). 3개 서브라인 모두 단품 수준으로 통합 랭킹 중위권.</li>' +
    '<li><strong>라엘 기본(26위)보다 낮은 이유:</strong> 라엘 기본 라인은 리뷰 4.2만 건+평점 4.9로 리뷰신뢰도 점수가 압도적으로 높음. 이너시아 더 퍼펙션은 리뷰 1.3만 건·평점 4.8로 리뷰신뢰도에서 라엘에 미치지 못함. 단, 이너시아는 올리브영+쿠팡 2채널 입점으로 커버리지 보너스(+10)를 받아 라엘(단일채널 +6)보다 커버리지 점수는 더 높음.</li>' +
    '<li><strong>더 쿨(63위)이 가장 낮은 이유:</strong> 올리브영 단일 입점(커버리지 60) + 리뷰 575건으로 리뷰신뢰도 점수가 매우 낮음. 신규 라인(8월 올영픽)으로 리뷰 축적이 덜 진행됨.</li>' +
    '<li><strong>핵심 인사이트:</strong> 이너시아는 라엘과 같은 프리미엄 유기농 순면 생리대지만, 리뷰 볼륨(1.2~1.3만 건)이 라엘 기본(4.2만 건)의 약 1/3 수준이라 통합 점수에서 밀림. 다만 2채널 입점 덕에 라엘의 다른 서브라인(프리미엄 56위·에어리쿨 60위·무표백 61위)보다는 순위가 높음.</li>' +
    '</ul></div>';

  var sourceHtml = '<div style="margin-top:var(--space-4);font-size:0.72rem;color:var(--color-text-faint);line-height:1.5">' +
    '데이터 출처: 올리브영 제품 상세 페이지 + 쿠팡 브랜드샵 크롤링 (2026-08-27). 더 프리즘: <a href="https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000187776" target="_blank" rel="noopener">생리대</a>, <a href="https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000195421" target="_blank" rel="noopener">입는오버나이트</a>, <a href="https://www.coupang.com/vp/products/7303692442" target="_blank" rel="noopener">팬티라이너</a> / 더 퍼펙션: <a href="https://www.coupang.com/vp/products/8106839172" target="_blank" rel="noopener">쿠팡</a>, <a href="https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000211867" target="_blank" rel="noopener">올리브영</a> / 더 쿨: <a href="https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000257283" target="_blank" rel="noopener">생리대</a>, <a href="https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A000000260492" target="_blank" rel="noopener">입는오버나이트</a> (올리브영 단독). 쿠팡 카테고리순위는 IP 차단으로 미수집.' +
    '</div>';

  el.innerHTML = summaryHtml + detailHtml + insightHtml + sourceHtml;
};
