def apply_risk(price, side, sl_percent=2, tp_percent=5):
    if side == "BUY":
        sl = price * (1 - sl_percent / 100)
        tp = price * (1 + tp_percent / 100)
    else:
        sl = price * (1 + sl_percent / 100)
        tp = price * (1 - tp_percent / 100)

    return sl, tp