import pandas as pd
import numpy as np
import datetime as dt
import yaml
from MIALibraries.Path import Path

with open(Path.MAPPING_BUFFER_PATH()) as f:
    doc = yaml.load(f)

start_time = dt.datetime.now()

event_table = pd.read_csv(
    '/home/ubuntu/tuple_client/%s.csv'%doc['table_map']['EVENT_LOG'],
    index_col = None,
    sep='|',
    usecols=[doc['column_map']['EVENT_LOG']['cust_id'],
             doc['column_map']['EVENT_LOG']['product_id'],
             doc['column_map']['EVENT_LOG']['timestamp']])
print "df created"
event_table.rename(columns={doc['column_map']['EVENT_LOG']['cust_id']:'cust_id'},inplace=True)
event_table.rename(columns={doc['column_map']['EVENT_LOG']['product_id']:'product_id'},inplace=True)
event_table.rename(columns={doc['column_map']['EVENT_LOG']['timestamp']:'timestamp'},inplace=True)
event_table['timestamp'] = pd.to_datetime(event_table['timestamp'])
group_data = event_table.groupby(['cust_id', 'product_id']).size()
group_data = group_data.reset_index()
group_data.rename(columns={0:'counter'}, inplace = True)
print "done"
repeated_data = group_data.query('counter != 1')
repeated_data.reset_index(drop=True, inplace=True)
xyz = pd.merge(event_table, repeated_data, on=['cust_id', 'product_id'], how='right')
print "tables merged"
dates = xyz.groupby(['cust_id', 'product_id'])['timestamp'].agg({'maxi_date' : np.max, 'mini_date' : np.min}).reset_index()
dates['time'] = dates['maxi_date'] - dates['mini_date']
print "time calculated"
del dates['maxi_date']
del dates['mini_date']

cust_repur = pd.merge(dates, xyz, on=['cust_id', 'product_id'], how='right')
print "merge complete"
cust_repur.reset_index(drop=True, inplace=True)
cust_repur_original = cust_repur
cust_repur_original.reset_index(drop=True,inplace=True)
cust_repur_original['repurchase_time'] = ((cust_repur_original['time']-pd.Timedelta(days=1)) / (cust_repur_original['counter']-1))
print cust_repur_original.head()
del cust_repur
del dates
del repeated_data
del group_data

print "tables deleted"

cust_repur_original['repurchase_int'] = cust_repur_original.repurchase_time.astype('timedelta64[D]')
print cust_repur_original.head()
repur_sum = cust_repur_original.groupby(['product_id'])['repurchase_int'].sum().reset_index().rename(columns= {0:'counter'})
repur_count = cust_repur_original.groupby(['product_id','cust_id']).size().reset_index().rename(columns={0:'counter'})
repur_count_final = repur_count.groupby(['product_id'])['counter'].count().reset_index().rename(columns={'counter':'cust_count'})
print "merging table"
art_products = pd.merge(repur_sum, repur_count_final, on=['product_id'])
art_products['average_repurchase_time'] = art_products['repurchase_int'] / art_products['cust_count']
print "art calculated"

del art_products['repurchase_int']
del art_products['cust_count']

cust_repur_original['time_diff'] = dt.date.today() - cust_repur_original["timestamp"].dt.date
print "time diff calculated"
cust_repur_original['time_diff_int'] = cust_repur_original.time_diff.astype('timedelta64[D]')

cust_repur_original.counter = cust_repur_original.counter.fillna(0)

cust_repur_original_final = cust_repur_original.merge(art_products, on=['product_id'])

print "merge completed"

cust_repur_original_final.repurchase_int.fillna(cust_repur_original_final.average_repurchase_time, inplace=True)

cust_repur_original_final['depriotarize'] = np.where(cust_repur_original_final['time_diff_int'] > cust_repur_original_final['repurchase_int'], 'Recommend', 'Do_not_recommend')

del cust_repur_original_final['timestamp']
del cust_repur_original_final['time']
del cust_repur_original_final['counter']
del cust_repur_original_final['repurchase_time']
del cust_repur_original_final['repurchase_int']
del cust_repur_original_final['time_diff']
del cust_repur_original_final['time_diff_int']
del cust_repur_original_final['average_repurchase_time']

print cust_repur_original_final.head()
print cust_repur_original_final.shape
print cust_repur_original_final.depriotarize.unique()
print "rt_completed"
print dt.datetime.now() - start_time


####################################affinity################################


print "calculating affinity"

del event_table['timestamp']
grp_cust = event_table.groupby('cust_id').count().reset_index()
grp_cust.rename(columns={'product_id':'counter'}, inplace=True)
grp_cust_df_1 = grp_cust.query('counter != 1')
grp_cust_df_1.reset_index(drop=True, inplace=True)
cust = grp_cust_df_1[['cust_id']]
final_data = event_table.merge(cust, on='cust_id')
cust_prod_comb = final_data.groupby(['cust_id','product_id']).size().reset_index().rename(columns={0:'counter'})
affinity_df = cust_prod_comb.merge(grp_cust_df_1, on='cust_id')
affinity_df.rename(columns={'counter_x':'combination'}, inplace=True)
affinity_df.rename(columns={'counter_y':'visits'}, inplace=True)
affinity_df['affinity'] = affinity_df['combination'] / affinity_df['visits'] * 100
affinity_df['affinity_round'] = affinity_df.affinity.round()
affinity_user_df = affinity_df[['cust_id','affinity_round']]
affinity_user_df1 = affinity_user_df.drop_duplicates('cust_id').reset_index(drop = True)
affinity_user_comb = affinity_user_df1.groupby(['affinity_round','cust_id']).size().reset_index().rename(columns={0:'users_count'})
affinity_user_comb_df = affinity_user_comb.groupby(by=['affinity_round'])['users_count'].sum()
affinity_user_comb_df = affinity_user_comb_df.to_frame()
affinity_user_comb_df.reset_index(inplace=True)
affinity_user_comb_df.sort_index(ascending=False,inplace=True)
affinity_user_comb_df['user_per'] = affinity_user_comb_df['users_count']/affinity_user_comb_df['users_count'].sum() * 100
affinity_user_comb_df['aggregated_per'] = affinity_user_comb_df.user_per.cumsum()
affinity_user_comb_df['round_aggr'] = affinity_user_comb_df.aggregated_per.round()

del event_table
del grp_cust
del grp_cust_df_1
del cust
del final_data
del cust_prod_comb

print "tables deleted"

a = affinity_user_comb_df.loc[affinity_user_comb_df['round_aggr'] <= 2]
a.reset_index(drop=True, inplace=True)
a_value = a.affinity_round.loc[a['round_aggr'] <= 2]
a_value = a_value.tolist()

if len(a_value) == 0:
    min_a = None
else:
    min_a = min(a_value)


b = affinity_user_comb_df.loc[(affinity_user_comb_df['round_aggr'] >2) &
                                       (affinity_user_comb_df['round_aggr'] <=10)]
b.reset_index(drop=True, inplace=True)
b_value = b.affinity_round.loc[(b['round_aggr'] >2) &
                          (b['round_aggr'] <=10)]
b_value = b_value.tolist()

if len(b_value) == 0:
    min_b = None
else:
    min_b = min(b_value)

c = affinity_user_comb_df.loc[(affinity_user_comb_df['round_aggr'] >10) &
                                       (affinity_user_comb_df['round_aggr'] <=25)]
c.reset_index(drop=True, inplace=True)
c_value = c.affinity_round.loc[(c['round_aggr'] >10) &
                                       (c['round_aggr'] <=25)]
c_value = c_value.tolist()

if len(c_value) == 0:
    min_c = None
else:
    min_c = min(c_value)

d = affinity_user_comb_df.loc[(affinity_user_comb_df['round_aggr'] >25) &
                                       (affinity_user_comb_df['round_aggr'] <=50)]
d.reset_index(drop=True, inplace=True)
d_value = d.affinity_round.loc[(d['round_aggr'] > 25) &
                          (d['round_aggr'] <=50)]
d_value= d_value.tolist()

if len(d_value) == 0:
    min_d = None
else:
    min_d = min(d_value)

e = affinity_user_comb_df.loc[affinity_user_comb_df['round_aggr'] > 50]
e.reset_index(drop=True, inplace=True)
e_value = e.affinity_round.loc[e['round_aggr'] > 50]
e_value = e_value.tolist()

if len(e_value) == 0:
    min_e = None
else:
    min_e = min(e_value)

affinity_df['recommendation_class'] = ""

if min_a is not None:
    affinity_df.loc[affinity_df['affinity_round'] >= min_a, 'recommendation_class'] = "Class_A"
if min_b is not None and min_a is not None:
    affinity_df.loc[(affinity_df['affinity_round'] >= min_b) & (affinity_df['affinity_round'] < min_a), 'recommendation_class'] = "Class_B"
if min_c is not None and min_b is not None:
    affinity_df.loc[(affinity_df['affinity_round'] >= min_c) & (affinity_df['affinity_round'] < min_b), 'recommendation_class'] = "Class_C"
if min_d is not None and min_c is not None:
    affinity_df.loc[(affinity_df['affinity_round'] >= min_d) & (affinity_df['affinity_round'] < min_c), 'recommendation_class'] = "Class_D"

affinity_df.loc[affinity_df["recommendation_class"] == '','recommendation_class'] = "Class_E"

del affinity_df['combination']
del affinity_df['visits']
del affinity_df['affinity']
del affinity_df['affinity_round']

print affinity_df.head()

print affinity_df.recommendation_class.unique()
print dt.datetime.now() - start_time

print "affinity completed"

event_fav = pd.merge(cust_repur_original_final,affinity_df, on = ['cust_id', 'product_id'])

print event_fav.shape

print event_fav.head()
print event_fav.depriotarize.unique()
print event_fav.recommendation_class.unique()

event_fav.to_csv('/home/ubuntu/tuple_client/event_fav.csv', mode='w', index=False)

print "completed"


'''write event_fav to database'''

print dt.datetime.now() - start_time