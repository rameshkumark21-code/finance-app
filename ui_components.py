import streamlit as st

def inject_custom_css():
    _CSS = """
    <link href='https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap' rel='stylesheet'>
    <style>
    /* ========================================================= */
    /* 🔴 THE MOBILE FIX: Forces columns to stack on small screens */
    /* ========================================================= */
    @media (max-width: 768px) {
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 8px !important;
        }
    }
    
    /* 🔴 THE BOTTOM NAV FIX: Prevents transparent buttons from stacking */
    .bnav-overlay-wrap [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
    }

    html,body,*{font-family:'Sora',sans-serif!important}
    .stApp{background:#080810;color:#e8e8f0; max-width: 100vw; overflow-x: hidden;}
    [data-testid='stHeader']{background:transparent!important}
    [data-testid='stToolbar']{display:none!important}
    h1,h2,h3,h4{letter-spacing:-0.3px;color:#e8e8f0}
    [data-testid='stVerticalBlock']>div{gap:0!important}
    div.block-container{padding-top:0.4rem!important;padding-bottom:3rem!important;padding-left:0.9rem!important;padding-right:0.9rem!important}
    
    .g-header{display:flex;justify-content:space-between;align-items:center;padding:8px 2px 10px;margin-bottom:0}
    .g-title{font-size:1.3rem;font-weight:800;color:#e8e8f0;letter-spacing:-1px}
    .g-title span{color:#f0a500}
    
    .bal-card{background:linear-gradient(135deg,#0f0f1a 0%,#0c0c18 100%);border:1px solid #1e1e30;border-radius:16px;padding:14px 16px;margin-bottom:10px;text-align:center}
    .bal-main{font-size:.85rem;font-weight:500;color:#555570;margin-bottom:8px;letter-spacing:.3px}
    .bal-main b{color:#e8e8f0;font-family:'JetBrains Mono',monospace!important;font-size:.95rem}
    .bal-row{display:flex;justify-content:center;gap:28px}
    .bal-stat{text-align:center}
    .bal-lbl{font-size:.58rem;text-transform:uppercase;letter-spacing:1.2px;color:#333355;font-weight:700;margin-bottom:2px}
    .bal-val{font-size:.9rem;font-weight:700;font-family:'JetBrains Mono',monospace!important}
    .bal-exp{color:#f75676}
    .bal-inc{color:#2dce89}
    
    .card{background:linear-gradient(145deg,#0f0f1a,#0c0c17);border:1px solid #1e1e2e;border-radius:16px;padding:14px 16px;margin-bottom:8px;box-shadow:0 4px 20px rgba(0,0,0,.4)}
    .card-sm{background:#0d0d16;border:1px solid #191928;border-radius:12px;padding:10px 13px;margin-bottom:6px}
    .card-amber{border-color:rgba(240,165,0,.25)!important;box-shadow:0 0 0 1px rgba(240,165,0,.1),0 4px 16px rgba(240,165,0,.06)!important}
    .card-red{border-color:rgba(247,86,118,.22)!important}
    .card-green{border-color:rgba(45,206,137,.22)!important}
    
    .hero-card{background:linear-gradient(135deg,#0f0f1e 0%,#0c0e1c 100%);border:1px solid #1e2038;border-radius:18px;padding:18px 18px 14px;margin-bottom:10px;box-shadow:0 8px 32px rgba(0,0,0,.45)}
    .hero-amount{font-size:2.1rem;font-weight:700;letter-spacing:-1.5px;color:#e8e8f0;font-family:'JetBrains Mono',monospace!important;margin-top:4px}
    .hero-row{display:flex;justify-content:space-between;align-items:flex-end}
    .hero-today-val{font-size:1.05rem;font-weight:700;color:#f0a500;text-align:right;font-family:'JetBrains Mono',monospace!important}
    .hero-today-lbl{font-size:.58rem;color:#333355;text-transform:uppercase;letter-spacing:1.2px;text-align:right;margin-bottom:3px}
    
    .tile{background:linear-gradient(145deg,#0f0f1a,#0c0c17);border:1px solid #1e1e2e;border-radius:14px;padding:11px 14px;margin-bottom:6px}
    .tile-accent{height:3px;border-radius:2px;margin-bottom:8px}
    .tile-label{color:#333355;font-size:.6rem;text-transform:uppercase;letter-spacing:1.5px;font-weight:600}
    .tile-value{font-size:1.45rem;font-weight:700;margin-top:3px;letter-spacing:-.8px;color:#e8e8f0;font-family:'JetBrains Mono',monospace!important}
    .tile-sub{font-size:.72rem;margin-top:3px;color:#444460}
    .trend-up{color:#f75676;font-weight:600}
    .trend-down{color:#2dce89;font-weight:600}
    .trend-flat{color:#333355}
    
    .mini-tile{background:#0d0d16;border:1px solid #191928;border-radius:12px;padding:9px 12px}
    .mini-tile-lbl{font-size:.58rem;color:#333355;text-transform:uppercase;letter-spacing:1.1px;font-weight:600}
    .mini-tile-val{font-size:1rem;font-weight:700;letter-spacing:-.5px;font-family:'JetBrains Mono',monospace!important;margin-top:2px}
    .mini-tile-sub{font-size:.63rem;color:#333355;margin-top:2px}
    
    .prog-wrap{margin-top:6px}
    .prog-track{background:#161620;border-radius:6px;height:6px;overflow:hidden}
    .prog-fill{height:6px;border-radius:6px;transition:width .5s ease}
    .prog-meta{display:flex;justify-content:space-between;margin-top:3px;font-size:.63rem;color:#333355}
    
    .sec-head{font-size:.6rem;text-transform:uppercase;letter-spacing:2px;color:#2a2a42;font-weight:700;margin:14px 0 7px;padding-left:2px}
    
    .cat-row{display:flex;align-items:center;justify-content:space-between;padding:9px 12px;border-radius:10px;margin-bottom:4px;background:#0d0d16;border:1px solid #191928}
    .cat-name{font-size:.83rem;font-weight:500;color:#ccc;flex:1}
    .cat-bar-wrap{width:48px;height:3px;background:#191928;border-radius:2px;margin:0 8px;flex-shrink:0}
    .cat-bar-fill{height:3px;border-radius:2px;background:#f0a500}
    .cat-amt{font-size:.83rem;font-weight:600;color:#e8e8f0;white-space:nowrap;font-family:'JetBrains Mono',monospace!important}
    
    .budget-row{padding:11px 14px;border-radius:12px;background:#0d0d16;border:1px solid #191928;margin-bottom:7px}
    .budget-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:5px}
    .budget-name{font-size:.83rem;font-weight:600;color:#ccc}
    .budget-nums{font-size:.7rem;color:#333355;font-family:'JetBrains Mono',monospace!important}
    
    .rec-card{background:#0d0d16;border:1px solid #1e1e2e;border-radius:12px;padding:11px 14px;margin-bottom:5px}
    .rec-fired{border-left:3px solid #2dce89}
    .rec-pending{border-left:3px solid #f0a500}
    .rec-title{font-size:.88rem;font-weight:600;color:#e0e0e0}
    .rec-meta{font-size:.7rem;color:#333355;margin-top:2px;font-family:'JetBrains Mono',monospace!important}
    
    .catlist-row{font-size:.86rem;font-weight:500;color:#ccc;padding:8px 0;border-bottom:1px solid #111120}
    
    .empty-box{text-align:center;padding:40px 20px}
    .empty-box .ico{font-size:2rem;margin-bottom:10px;opacity:.4}
    .empty-box .msg{font-size:.84rem;line-height:1.6;color:#333355}
    
    .cat-hero{background:#0d0d16;border:1px solid #1e1e2e;border-radius:14px;padding:13px 15px;margin-bottom:6px}
    .cat-hero-name{font-size:.95rem;font-weight:700;color:#e8e8f0}
    .cat-hero-meta{font-size:.68rem;color:#333355;margin-top:2px}
    .cat-hero-amt{font-size:1.1rem;font-weight:700;color:#f0a500;white-space:nowrap;font-family:'JetBrains Mono',monospace!important}
    
    .chip{display:inline-block;background:#101828;color:#7c9eff;border-radius:5px;font-size:.62rem;font-weight:600;padding:1px 6px;margin-right:3px;letter-spacing:.3px}
    
    .review-card{background:#0d0d16;border:1px solid #2a1f08;border-left:3px solid #f0a500;border-radius:14px;padding:13px 15px;margin-bottom:10px}
    .review-badge-sug{display:inline-block;background:#2a1f05;color:#f0a500;border-radius:5px;font-size:.62rem;font-weight:600;padding:1px 6px}
    
    .badge-anomaly{display:inline-block;background:#150505;color:#f75676;border-radius:5px;font-size:.62rem;font-weight:700;padding:1px 6px;margin-right:3px}
    .badge-dup{display:inline-block;background:#150e05;color:#fb923c;border-radius:5px;font-size:.62rem;font-weight:700;padding:1px 6px;margin-right:3px}
    .badge-recur{display:inline-block;background:#040e18;color:#60a5fa;border-radius:5px;font-size:.62rem;font-weight:700;padding:1px 6px;margin-right:3px}
    .badge-intel{display:inline-block;background:#041408;color:#4ade80;border-radius:5px;font-size:.62rem;font-weight:700;padding:1px 6px;margin-right:3px}
    
    .anomaly-panel{background:#0a0305;border:1px solid #180808;border-left:3px solid #f75676;border-radius:12px;padding:10px 13px;margin-bottom:10px}
    .anomaly-panel-title{font-size:.67rem;font-weight:700;color:#f75676;margin-bottom:6px;text-transform:uppercase;letter-spacing:1.2px}
    .anomaly-item{display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:.75rem;border-bottom:1px solid #100505}
    
    .log-row{display:flex;justify-content:space-between;align-items:center;padding:7px 12px;border-bottom:1px solid #111120;font-size:.75rem}
    .log-ok{color:#2dce89;font-weight:600}
    .log-err{color:#f75676;font-weight:600}
    .log-num{color:#e8e8f0;font-weight:600;font-family:'JetBrains Mono',monospace!important}
    .log-dim{color:#333355}
    
    .sync-card{background:#0d0d16;border:1px solid #1e1e2e;border-radius:14px;padding:15px 17px;margin-bottom:10px}
    .sync-title{font-size:.9rem;font-weight:700;color:#e8e8f0;margin-bottom:4px}
    .sync-meta{font-size:.73rem;color:#333355}
    
    .analytics-card{background:#0d0d16;border:1px solid #1e1e2e;border-radius:14px;padding:15px 17px;margin-bottom:10px}
    .analytics-title{font-size:.6rem;text-transform:uppercase;letter-spacing:1.5px;color:#2a2a42;font-weight:700;margin-bottom:12px}
    .heatmap-wrap{overflow-x:auto;padding:2px 0}
    .dow-row{display:flex;align-items:center;margin-bottom:5px;gap:7px}
    .dow-label{font-size:.67rem;color:#333355;width:26px;flex-shrink:0;text-align:right}
    .dow-bar-fill{height:14px;border-radius:4px;min-width:3px}
    .dow-bar-amt{font-size:.64rem;color:#333355;white-space:nowrap;font-family:'JetBrains Mono',monospace!important}
    .merchant-rank-row{display:flex;align-items:center;justify-content:space-between;padding:7px 0;border-bottom:1px solid #111120}
    .merchant-rank-name{font-size:.8rem;color:#ccc;flex:1}
    .merchant-rank-bar{height:3px;border-radius:2px;background:#f0a500;margin:0 8px;flex-shrink:0}
    .merchant-rank-amt{font-size:.82rem;font-weight:600;color:#f0a500;white-space:nowrap;font-family:'JetBrains Mono',monospace!important}
    
    .sug-chip-row{background:rgba(240,165,0,.05);border:1px solid rgba(240,165,0,.18);border-radius:10px;padding:7px 11px;margin-bottom:7px;display:flex;align-items:center;justify-content:space-between}
    .sug-chip-label{font-size:.63rem;color:#555;margin-bottom:2px}
    .sug-chip-val{font-size:.86rem;font-weight:600;color:#f0a500}
    
    .queue-pill{display:inline-block;background:#0b0b14;border:1px solid #1e1e2e;border-radius:20px;padding:3px 11px;font-size:.67rem;color:#333355;margin-bottom:9px}
    
    .txn-row{display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid #111120}
    .txn-amt{font-size:.9rem;font-weight:700;color:#e8e8f0;white-space:nowrap;font-family:'JetBrains Mono',monospace!important;min-width:70px}
    .txn-cat{font-size:.83rem;font-weight:600;color:#ccc}
    .txn-meta{font-size:.63rem;color:#2a2a42;margin-top:2px}
    .txn-note{font-size:.63rem;color:#555570;font-style:italic}
    
    .monthly-bar-row{display:flex;align-items:center;margin-bottom:5px;gap:7px}
    .monthly-bar-lbl{font-size:.64rem;color:#333355;width:42px;flex-shrink:0;text-align:right}
    .monthly-bar-amt{font-size:.64rem;color:#f0a500;white-space:nowrap;margin-left:4px;font-family:'JetBrains Mono',monospace!important}
    
    .split-row{background:#09090e;border:1px solid #2a2a10;border-left:2px solid #f0a500;border-radius:8px;padding:9px 13px;margin-bottom:7px}
    
    div[data-testid='stDialog']{background:#0c0c15!important;border:1px solid #1e1e2e!important;border-radius:20px!important}
    [data-testid='stTextInput'] input,[data-testid='stNumberInput'] input{background:#0d0d17!important;border:1px solid #1e1e2e!important;border-radius:9px!important;color:#e8e8f0!important}
    [data-testid='stSelectbox']>div>div{background:#0d0d17!important;border:1px solid #1e1e2e!important;border-radius:9px!important}
    [data-testid='stExpander']{background:#0b0b14!important;border:1px solid #191928!important;border-radius:10px!important;margin-bottom:5px}
    [data-testid='stExpander'] summary{font-size:.83rem!important;font-weight:500!important;color:#aaa!important}
    [data-testid='stForm']{border:1px solid #191928!important;border-radius:12px!important;padding:12px!important;background:#090912!important}
    .stAlert{border-radius:10px!important}
    [data-testid='stMultiSelect'] span{background:#101828!important;color:#7c9eff!important;border-radius:5px!important;font-size:.7rem!important}
    
    /* Extra Bottom Nav Container Fix */
    .bnav-wrap {
        display: flex;
        justify-content: space-around;
        align-items: center;
        background: #0d0d16;
        border-top: 1px solid #1e1e2e;
        padding: 8px 0;
        position: fixed;
        bottom: 0;
        width: 100%;
        left: 0;
        z-index: 9998;
    }
    .bnav-item { display: flex; flex-direction: column; align-items: center; color: #555570; font-size: 0.65rem; flex: 1; }
    .bnav-item.active { color: #f0a500; }
    .bnav-icon { font-size: 1.2rem; margin-bottom: 2px; }
    </style>
    """
    st.markdown(_CSS, unsafe_allow_html=True)
