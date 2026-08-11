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
    <p class="sub">{{ s.period.from }} ~ {{ s.period.to }} · {{ s.snapshots }}회차 · 종목 콜 <b>{{ s.overall.calls }}건</b></p>
  </header>

  {% if s.vs_bench and s.vs_bench.size > 0 %}
  <section class="card yardstick">
    <h2>📊 기준선을 이겼는가 — <span class="{% if s.beat_bench > 0 %}u{% else %}d{% endif %}">{{ s.beat_bench }}승 {{ s.accounts | minus: s.beat_bench }}패</span></h2>
    <p class="mut small">기준선 = 같은 기간 코스피. 개시일이 달라 각자 개시일 기준으로 자릅니다.</p>
    <div class="scroll"><table>
      <thead><tr><th>계좌</th><th>개시</th><th>수익률</th><th>기준선</th><th>초과</th></tr></thead>
      <tbody>
        {% for v in s.vs_bench %}
        <tr>
          <td class="nm">{{ v.persona }} <span class="mut">{{ v.days }}일차</span></td>
          <td class="mut">{{ v.since }}</td>
          <td class="{% if v.return_pct >= 0 %}u{% else %}d{% endif %}">{% if v.return_pct >= 0 %}+{% endif %}{{ v.return_pct }}%</td>
          <td class="mut">{% if v.bench_pct >= 0 %}+{% endif %}{{ v.bench_pct }}%</td>
          <td class="big {% if v.excess_pct >= 0 %}u{% else %}d{% endif %}">{% if v.excess_pct >= 0 %}+{% endif %}{{ v.excess_pct }}%p</td>
        </tr>
        {% endfor %}
      </tbody>
    </table></div>
  </section>
  {% endif %}

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
    <p class="mut small">초과수익 = 종목 수익률 − 같은 기간 지수(🇰🇷 코스피 / 🇺🇸 S&amp;P500). 매도는 부호를 뒤집어 채점.</p>
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
    <p class="mut small">보유 종목이 겹칠수록 계좌를 나눈 의미가 없습니다.</p>
    <div class="ovl">
      {% for p in s.overlap.holdings_pairs %}
      <div class="ov"><span class="pr">{{ p.pair }}</span><span class="jc">{{ p.jaccard_pct }}%</span></div>
      {% endfor %}
    </div>
    <p class="mut small">같은 날 같은 종목 동시 매수는 {{ s.overlap.shared_2plus_pct }}%.</p>
  </section>

  <section class="card warn">
    <h2>⚠️ 한계</h2>
    <ul class="pfr">
      <li>{{ s.snapshots }}회차 · 콜 {{ s.overall.calls }}건 — 표본 부족</li>
      <li>여러 계좌가 같은 종목을 사면 실질 표본은 더 적습니다</li>
      <li>노이즈 바닥 {{ s.noise.avg_daily_gap }}%p 이하 차이는 실력이 아닙니다</li>
      <li>베타 미보정 · 수수료·세금 미반영 · 투자 조언 아님</li>
    </ul>
  </section>

  <p class="mut small" style="margin:10px 4px 0"><a href="https://github.com/gks930620/stock-daily/tree/main/portfolio/orders">주문서</a> · <a href="https://github.com/gks930620/stock-daily/tree/main/data">시세</a> 원본 대조 가능 · <a href="{{ '/portfolio/' | relative_url }}">← 포트폴리오</a></p>
</div>

<style>
.sb{--u:var(--up);--dn:var(--down);}
.sb .u{color:var(--u);} .sb .d{color:var(--dn);} .sb .mut{color:var(--muted);} .sb .small{font-size:13px;}
.sb .hh h1{font-size:clamp(28px,5.4vw,42px);margin:.15em 0 .25em;letter-spacing:-.03em;}
.sb .hh .one{font-size:clamp(15px,2.1vw,18px);font-weight:700;margin:0 0 6px;}
.sb .hh .sub{font-size:13.5px;color:var(--muted);margin:0 0 4px;}
.sb .lead-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:18px 0 4px;}
.sb .lc{position:relative;background:var(--surface);border-radius:var(--radius);padding:17px 18px;box-shadow:var(--sh);}
.sb .lc::before{content:"";position:absolute;left:16px;right:16px;top:0;height:2px;border-radius:0 0 3px 3px;background:var(--grad);opacity:.16;}
.sb .lc .k{font-size:12.5px;color:var(--muted);font-weight:700;}
.sb .lc .v{font-size:29px;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums;margin:3px 0 1px;}
.sb .lc .n{font-size:11.5px;color:var(--muted);}
.sb .card{position:relative;background:var(--surface);border-radius:var(--radius);padding:22px 24px;margin-top:16px;box-shadow:var(--sh);}
.sb .card::before{content:"";position:absolute;left:16px;right:16px;top:0;height:2px;border-radius:0 0 3px 3px;background:var(--grad);opacity:.16;}
.sb .card h2{margin:0 0 10px;font-size:16.5px;}
.sb .card.warn::before{background:linear-gradient(135deg,var(--warn),var(--up));opacity:.5;}
.sb .card.yardstick{margin-top:18px;}
.sb .card.yardstick::before{opacity:.85;height:3px;}
.sb .card.yardstick h2{font-size:18px;}
.sb td.big{font-size:15px;font-weight:800;}
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
