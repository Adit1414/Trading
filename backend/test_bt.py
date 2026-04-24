import traceback
import pandas as pd
from numpy import random
random.seed(0)
dates = pd.date_range('2020-01-01', periods=100, freq='D')
data1 = pd.DataFrame({
    'Open': random.randn(100)*10+100,
    'High': random.randn(100)*10+105,
    'Low': random.randn(100)*10+95,
    'Close': random.randn(100)*10+100,
    'Volume': random.randint(100, 1000, 100)
}, index=dates)

from backtesting import Backtest, Strategy

class S(Strategy):
    def init(self): pass
    def next(self): pass

bt = Backtest(data1, S)
bt.run()
try:
    import bokeh.models.formatters
    _orig_formatter_init = bokeh.models.formatters.DatetimeTickFormatter.__init__
    def _patched_formatter_init(self, *args, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], str):
                kwargs[k] = v[0]
        _orig_formatter_init(self, *args, **kwargs)
    bokeh.models.formatters.DatetimeTickFormatter.__init__ = _patched_formatter_init

    bt.plot(filename='test.html', open_browser=False, resample=False)
    print('Success!')
except Exception as e:
    print('Error:')
    traceback.print_exc()
