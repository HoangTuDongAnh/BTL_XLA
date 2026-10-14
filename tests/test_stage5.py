import numpy as np
import pandas as pd
from src.stage5.robustness import paired,block_bootstrap,circular_shift_test
from src.stage5.aod_evaluation import temporal_prediction

def test_lag_and_season_boundary():
    data=pd.DataFrame({'period':['May_Jun_2025']*3+['Oct_Nov_2025']*2,
      'date':['2025-06-28','2025-06-29','2025-06-30','2025-10-01','2025-10-02'],
      'x':[1,2,3,40,50],'y':[1,2,3,40,50]})
    result=paired(data,'x','y',1)
    assert len(result)==3
    assert 3 not in result.x.to_list()

def test_bootstrap_seed():
    x=np.arange(40.0);y=x+np.sin(x)
    a=block_bootstrap(x,y,reps=50,seed=99);b=block_bootstrap(x,y,reps=50,seed=99)
    assert np.array_equal(a,b)

def test_shift_ignores_nans():
    x=np.arange(50.0);y=x.copy();y[::3]=np.nan
    r,p,n=circular_shift_test(x,y)
    assert abs(r-1)<1e-10 and np.isfinite(p) and n>10

def test_temporal_and_nodata():
    a=np.array([[1,np.nan]],np.float32);b=np.array([[3,5]],np.float32)
    out=temporal_prediction(a,b)
    assert out[0,0]==2 and np.isnan(out[0,1])
