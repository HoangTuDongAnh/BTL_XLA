import pandas as pd
from src.stage4.analyze import pairs,calculate

def test_lag_calendar_and_season():
    data=pd.DataFrame({'period':['May_Jun_2025']*2+['Oct_Nov_2025']*2,'date':['2025-06-29','2025-06-30','2025-10-01','2025-10-02'],'x':[1,2,3,4],'y':[10,20,30,40]})
    matched=pairs(data,'x','y',1)
    assert list(zip(matched.date,matched.x,matched.y))==[('2025-06-29',1,20),('2025-10-01',3,40)]

def test_missing_and_insufficient_pairs():
    data=pd.DataFrame({'period':['May_Jun_2025']*4,'date':['2025-05-01','2025-05-02','2025-05-03','2025-05-04'],'x':[1,2,3,4],'y':[2,None,4,5]})
    res=calculate(data,comparisons={'x_y':('x','y')},min_n=8)
    assert len(res)==12 and res.pearson_r.isna().all()
