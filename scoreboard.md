---
layout: default
title: AI 채점판 — 진짜 잘하는가
permalink: /scoreboard/
---

{% assign s = site.data.scoreboard %}

<div class="sb">
  {% include pf-switcher.html %}

  <header class="hh">
    <h1>진짜 잘하는가</h1>
    <p class="one">계좌 수익률은 하루 1표본 · <b>종목 콜은 하루 수십 표본</b></p>
    <p class="sub">{{ s.period.from }} ~ {{ s.period.to }} · {{ s.snapshots }}회차 · 종목 콜 <b>{{ s.overall.calls }}건</b> 소급 채점</p>
  </header>

  <div class="lead-cards">
    <div class="lc">
      <div class="k">전체 적중률 <span class="mut">(현재까지)</span></div>
      <div class="v {% if s.overall.now.hit_pct >= 50 %}u{% else %}d{% endif %}">{{ s.overall.now.hit_pct }}%</div>
      <div class="n">50%가 동전던지기</div>
    </div>
    <div class="lc">
      <div class="k">평균 초과수익</div>
      <div class="v {% if s.overall.now.avg_excess >= 0 %}u{% else %}d{% endif %}">{% if s.overall.now.avg_excess >= 0 %}+{% endif %}{{ s.overall.now.avg_excess }}%p</div>
      <div class="n">시장 대비 · 콜 1건당</div>
    </div>
    <div class="lc">
      <div class="k">노이즈 바닥</div>
      <div class="v">{{ s.noise.avg_daily_gap }}%p</div>
      <div class="n">동일 지시문 2인의 일간 격차</div>
    </div>
    <div class="lc">
      <div class="k">보유 겹침</div>
      <div class="v">{{ s.overlap.holdings_jaccard_avg_pct }}%</div>
      <div class="n">계좌 쌍 평균 · 높으면 분산 아님</div>
    </div>
  </div>

  <section class="card">
    <h2>보유 기간별 성적</h2>
    <p class="mut small">초과수익 = 종목 수익률 − 같은 기간 벤치마크(🇰🇷 코스피 / 🇺🇸 S&amp;P500). 시장이 오르내린 몫을 빼야 <b>종목 고르는 실력</b>만 남습니다. 매도는 부호를 뒤집어 채점합니다(팔고 나서 더 빠졌으면 적중).</p>
    <div class="scroll"><table>
      <thead><tr><th>계좌</th>
        {% for hz in s.horizons %}<th colspan="2">{{ hz.label }}</th>{% endfor %}
      </tr>
      <tr class="sub2"><th></th>
        {% for hz in s.horizons %}<th>적중률</th><th>평균초과</th>{% endfor %}
      </tr></thead>
      <tbody>
        {% for row in s.by_persona %}
        <tr>
          <td class="nm">{{ row[1].name }} <span class="mut">{{ row[1].calls }}콜</span></td>
          {% for hz in s.horizons %}
            {% assign v = row[1][hz.key] %}
            {% if v %}
              <td class="{% if v.hit_pct >= 50 %}u{% else %}d{% endif %}">{{ v.hit_pct }}%</td>
              <td class="{% if v.avg_excess >= 0 %}u{% else %}d{% endif %}">{% if v.avg_excess >= 0 %}+{% endif %}{{ v.avg_excess }}%p</td>
            {% else %}<td class="mut">—</td><td class="mut">—</td>{% endif %}
          {% endfor %}
        </tr>
        {% endfor %}
        <tr class="tot">
          <td class="nm">전체 <span class="mut">{{ s.overall.calls }}콜</span></td>
          {% for hz in s.horizons %}
            {% assign v = s.overall[hz.key] %}
            {% if v %}
              <td class="{% if v.hit_pct >= 50 %}u{% else %}d{% endif %}">{{ v.hit_pct }}%</td>
              <td class="{% if v.avg_excess >= 0 %}u{% else %}d{% endif %}">{% if v.avg_excess >= 0 %}+{% endif %}{{ v.avg_excess }}%p</td>
            {% else %}<td class="mut">—</td><td class="mut">—</td>{% endif %}
          {% endfor %}
        </tr>
      </tbody>
    </table></div>
  </section>

  <div class="two">
    <section class="card">
      <h2>🔴 가장 잘한 콜</h2>
      {% for c in s.best %}
      <div class="cl"><span class="ex u">+{{ c.excess }}%p</span>
        <b>{{ c.name }}</b> <span class="mut">{{ c.action }} · {{ c.date }} · {{ c.persona }}</span></div>
      {% endfor %}
    </section>
    <section class="card">
      <h2>🔵 가장 못한 콜</h2>
      {% for c in s.worst %}
      <div class="cl"><span class="ex d">{{ c.excess }}%p</span>
        <b>{{ c.name }}</b> <span class="mut">{{ c.action }} · {{ c.date }} · {{ c.persona }}</span></div>
      {% endfor %}
    </section>
  </div>

  <section class="card">
    <h2>4개의 뇌인가, 하나인가</h2>
    <p class="mut small">계좌를 4개로 나눈 이유는 <b>분산</b>입니다. 그런데 경로가 달라도 결국 같은 포트폴리오에 도달하면 나눈 의미가 없습니다. 그래서 <b>보유 겹침</b>으로 판정합니다.</p>
    <div class="ovl">
      {% for p in s.overlap.holdings_pairs %}
      <div class="ov"><span class="pr">{{ p.pair }}</span><span class="jc">{{ p.jaccard_pct }}%</span></div>
      {% endfor %}
    </div>
    <p class="mut small">주문 겹침(같은 날 같은 종목 동시 매수)은 {{ s.overlap.shared_2plus_pct }}%로 낮습니다 — 종목·타이밍은 갈립니다. 판정은 위의 보유 겹침으로 하세요.</p>
  </section>

  <section class="card warn">
    <h2>⚠️ 이 숫자를 믿을 때의 한계</h2>
    <ul class="pfr">
      <li><b>표본이 적습니다.</b> {{ s.snapshots }}회차 · 콜 {{ s.overall.calls }}건. 통계적 결론을 내리기엔 아직 부족합니다.</li>
      <li><b>콜이 서로 독립이 아닙니다.</b> 여러 계좌가 같은 종목을 사면 그만큼 실질 표본은 줄어듭니다 — 콜 수 ≠ 표본 수.</li>
      <li><b>노이즈 바닥이 {{ s.noise.avg_daily_gap }}%p</b>(최대 {{ s.noise.max_daily_gap }}%p)입니다. 완전히 동일한 지시문·모델의 두 계좌가 아무 이유 없이 그만큼 갈립니다. 이보다 작은 차이는 실력이 아닙니다.</li>
      <li>벤치마크는 지수, 콜은 개별 종목이라 <b>변동성(베타)이 보정되지 않았습니다.</b></li>
      <li>가상 매매 기록이며 <b>투자 조언이 아닙니다.</b></li>
    </ul>
  </section>

  <p class="mut small" style="margin:10px 4px 0">채점 코드: <code>scripts/scoreboard.py</code> · 원본은 커밋된 <code>portfolio/orders/</code>·<code>data/</code>와 대조 가능 · <a href="{{ '/portfolio/' | relative_url }}">← 포트폴리오</a></p>
</div>

<style>
.sb{--u:#d63c2f;--dn:#2563d0;}
.sb .u{color:var(--u);} .sb .d{color:var(--dn);} .sb .mut{color:var(--muted);} .sb .small{font-size:13px;}
.sb .hh h1{font-size:clamp(28px,5.4vw,42px);margin:.15em 0 .25em;letter-spacing:-.03em;}
.sb .hh .one{font-size:clamp(15px,2.1vw,18px);font-weight:700;margin:0 0 6px;}
.sb .hh .sub{font-size:13.5px;color:var(--muted);margin:0 0 4px;}
.sb .lead-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:18px 0 4px;}
.sb .lc{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:15px 16px;box-shadow:var(--shadow);}
.sb .lc .k{font-size:12.5px;color:var(--muted);font-weight:700;}
.sb .lc .v{font-size:29px;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums;margin:3px 0 1px;}
.sb .lc .n{font-size:11.5px;color:var(--muted);}
.sb .card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px 22px;margin-top:16px;box-shadow:var(--shadow);}
.sb .card h2{margin:0 0 10px;font-size:16.5px;}
.sb .card.warn{border-color:color-mix(in srgb,var(--u) 30%,var(--line));}
.sb .two{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;}
.sb .scroll{overflow-x:auto;}
.sb table{width:100%;border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums;min-width:620px;}
.sb th{font-size:12px;color:var(--muted);text-align:center;padding:6px 8px;border-bottom:2px solid var(--line);}
.sb thead tr.sub2 th{font-weight:600;font-size:11px;border-bottom:1px solid var(--line);}
.sb th:first-child{text-align:left;}
.sb td{padding:9px 8px;border-bottom:1px solid var(--line);text-align:center;font-weight:700;}
.sb td.nm{text-align:left;font-weight:800;white-space:nowrap;}
.sb td.nm .mut{font-weight:500;font-size:12px;}
.sb tr.tot td{border-top:2px solid var(--line);background:color-mix(in srgb,var(--bg) 55%,var(--card));}
.sb .cl{display:flex;align-items:baseline;gap:10px;padding:7px 0;border-bottom:1px solid var(--line);font-size:14px;}
.sb .cl:last-child{border-bottom:none;}
.sb .ex{font-weight:800;font-variant-numeric:tabular-nums;min-width:74px;}
.sb .ovl{display:flex;flex-direction:column;gap:6px;margin:10px 0;}
.sb .ov{display:flex;justify-content:space-between;align-items:center;font-size:13.5px;padding:6px 0;border-bottom:1px solid var(--line);}
.sb .ov .jc{font-weight:800;font-variant-numeric:tabular-nums;}
.sb .pfr{font-size:14px;color:var(--muted);padding-left:1.2em;margin:0;}
.sb .pfr li{margin:7px 0;}
</style>
