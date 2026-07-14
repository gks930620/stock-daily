---
layout: default
title: 가상 포트폴리오 · 3인 비교
permalink: /portfolio/
---

{% assign ids = "stable,aggressive,contrarian" | split: "," %}
{% assign accents = "stable:#2f9e7f,aggressive:#d6452f,contrarian:#7a5bd0" | split: "," %}

{%- assign best = -99999 -%}
{%- for id in ids -%}{%- assign key = 'portfolio-' | append: id -%}{%- assign pf = site.data[key] -%}{%- if pf.return_pct > best -%}{%- assign best = pf.return_pct -%}{%- endif -%}{%- endfor -%}

<div class="pfhub">
  {% include pf-switcher.html %}

  <header class="hh">
    <h1>같은 시장, 세 개의 뇌</h1>
    <p>성향이 다른 AI 3명이 <b>각자 1억 원</b>으로 굴린다. 매일 같은 리포트·같은 데이터를 보지만, 안정형은 지키고 공격형은 밀어붙이고 역발상형은 거꾸로 간다. <b>누가 진짜 고수인지</b>는 손익이 말한다.</p>
    <p class="note">📌 일별 손익 확정 = 매일 18:00 KST · 주문은 장 시작 전 결정 → 다음 개장 시가 체결(룩어헤드 불가) · 가상 매매</p>
  </header>

  <div class="grid">
    {% for id in ids %}
      {% assign key = 'portfolio-' | append: id %}
      {% assign pf = site.data[key] %}
      {% assign ac = "#666" %}
      {% for pair in accents %}{% assign kv = pair | split: ":" %}{% if kv[0] == id %}{% assign ac = kv[1] %}{% endif %}{% endfor %}
      <a class="pcard" href="{{ '/portfolio/' | append: id | append: '/' | relative_url }}" style="--ac:{{ ac }}">
        <div class="ptop">
          <span class="pemo">{{ pf.persona_emoji }}</span>
          <span class="pnm">{{ pf.persona_name }}</span>
          {% if best != 0 and pf.return_pct == best %}<span class="lead">🏆 선두</span>{% endif %}
        </div>
        <div class="ptag">{{ pf.persona_tag }}</div>
        <div class="ptot">{{ pf.total_value_str }}<small>원</small></div>
        <div class="pret {% if pf.return_pct >= 0 %}u{% else %}d{% endif %}">
          {% if pf.return_pct >= 0 %}▲ +{% else %}▼ {% endif %}{{ pf.return_pct }}%
          <span class="pday">오늘 {% if pf.day_chg_pct >= 0 %}+{% endif %}{{ pf.day_chg_pct }}%</span>
        </div>
        <div class="pmeta">
          <span>현금 <b>{{ pf.cash_weight_pct }}%</b></span>
          <span>보유 <b>{{ pf.holdings_view.size }}</b>종목</span>
          <span>{{ pf.days }}일차</span>
        </div>
        <div class="phold">
          {% if pf.holdings_view.size > 0 %}
            {% for h in pf.holdings_view limit:3 %}<span class="hp"><i style="background:{{ ac }}"></i>{{ h.name }} {{ h.weight_pct }}%</span>{% endfor %}
          {% else %}
            <span class="hp empty">아직 보유 없음 · 현금 100% (첫 매매 대기)</span>
          {% endif %}
        </div>
        <div class="pgo">자세히 보기 →</div>
      </a>
    {% endfor %}
  </div>

  <p class="foot">각 카드를 누르면 그 성향의 <b>보유종목·평단·매매일지·자산곡선</b>이 증권앱처럼 열립니다. · <a href="{{ '/' | relative_url }}">← 리포트</a></p>
</div>

<style>
.pfhub{--u:#d63c2f;--dn:#2563d0;}
.pfhub .hh h1{font-size:clamp(24px,4.6vw,32px);margin:.2em 0 .35em;letter-spacing:-.02em;}
.pfhub .hh p{font-size:15px;line-height:1.7;color:var(--text);margin:.3em 0;}
.pfhub .hh .note{font-size:12.5px;color:var(--muted);background:var(--card);border:1px solid var(--line);border-radius:9px;padding:8px 12px;margin-top:10px;}
.pfhub .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin:22px 0 10px;}
.pfhub .pcard{display:block;text-decoration:none;color:var(--text);background:var(--card);border:1px solid var(--line);border-top:4px solid var(--ac);border-radius:15px;padding:18px 19px;box-shadow:var(--shadow);transition:transform .12s,box-shadow .12s;}
.pfhub .pcard:hover{transform:translateY(-3px);box-shadow:0 10px 26px rgba(0,0,0,.13);}
.pfhub .ptop{display:flex;align-items:center;gap:9px;}
.pfhub .pemo{font-size:22px;}
.pfhub .pnm{font-size:18px;font-weight:800;letter-spacing:-.01em;}
.pfhub .lead{margin-left:auto;font-size:12px;font-weight:800;color:var(--ac);background:color-mix(in srgb,var(--ac) 14%,transparent);padding:3px 9px;border-radius:999px;}
.pfhub .ptag{font-size:12.5px;color:var(--muted);margin:7px 0 14px;line-height:1.45;min-height:2.6em;}
.pfhub .ptot{font-size:26px;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums;}
.pfhub .ptot small{font-size:.5em;font-weight:600;color:var(--muted);margin-left:2px;}
.pfhub .pret{font-size:16px;font-weight:800;margin:2px 0 12px;font-variant-numeric:tabular-nums;}
.pfhub .pret.u{color:var(--u);} .pfhub .pret.d{color:var(--dn);}
.pfhub .pret .pday{font-size:12px;font-weight:600;color:var(--muted);margin-left:6px;}
.pfhub .pmeta{display:flex;gap:14px;font-size:12.5px;color:var(--muted);padding:10px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);}
.pfhub .pmeta b{color:var(--text);}
.pfhub .phold{display:flex;flex-wrap:wrap;gap:7px 12px;margin:12px 0;min-height:2.4em;}
.pfhub .hp{font-size:12.5px;color:var(--text);display:inline-flex;align-items:center;}
.pfhub .hp i{width:8px;height:8px;border-radius:3px;margin-right:5px;display:inline-block;}
.pfhub .hp.empty{color:var(--muted);}
.pfhub .pgo{font-size:13px;font-weight:700;color:var(--ac);}
.pfhub .foot{font-size:13px;color:var(--muted);margin-top:8px;}
</style>
