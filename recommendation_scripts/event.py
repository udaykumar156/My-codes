from mapping import doc
import pandas as pd
import datetime as dt

start_time = dt.datetime.now()


event_table = pd.read_csv('/home/ubuntu/%s.csv'%(doc['table_map']['EVENT_LOG']),
              usecols=[doc['column_map']['EVENT_LOG']['cust_id'],
                       doc['column_map']['EVENT_LOG']['product_id'],
                       doc['column_map']['EVENT_LOG']['action_type']],
                sep = '|')

event_table.rename(columns={doc['column_map']['EVENT_LOG']['cust_id']:'cust_id'}, inplace=True)
event_table.rename(columns={doc['column_map']['EVENT_LOG']['product_id']:'product_id'}, inplace=True)
event_table.rename(columns={doc['column_map']['EVENT_LOG']['action_type']:'action_type'}, inplace=True)
# trans_table['cust_id'] = trans_table['cust_id'].astype('category')
# trans_table['cust_id'] = trans_table['cust_id'].cat.codes
# trans_table['product_id'] = trans_table['product_id'].astype('category')
# trans_table['product_id'] = trans_table['product_id'].cat.codes
print "table created"
grp_cust = event_table.groupby('cust_id').count().reset_index().rename(columns={'product_id':'value'})
del grp_cust['action_type']
grp_cust_cou = grp_cust.groupby(['value']).count().reset_index()
grp_cust_cou.rename(columns = {'value':'no_of_products'}, inplace=True)
grp_cust_cou.rename(columns = {'cust_id':'users_count'}, inplace=True)
grp_cust_cou = grp_cust_cou.sort_index(ascending = False)
grp_cust_cou['users_per'] = grp_cust_cou['users_count']/grp_cust_cou['users_count'].sum() * 100
grp_cust_cou['aggregated_per'] = grp_cust_cou.users_per.cumsum()
grp_cust_cou = grp_cust_cou.reset_index(drop=True)
threshold_df_cust = grp_cust_cou.loc[grp_cust_cou['aggregated_per'] > 85]
threshold_value_cust = threshold_df_cust.no_of_products.loc[threshold_df_cust['aggregated_per'] > 90]
threshold_value_cust = threshold_value_cust.reset_index(drop=True)
cust = grp_cust.loc[grp_cust['value'] > threshold_value_cust[0]]
cust = cust.reset_index(drop=True)
del cust['value']
print "customers created"
grp_prod = event_table.groupby(['product_id']).count().reset_index().rename(columns = {'cust_id':'value'})
del grp_prod['action_type']
grp_prod_cou = grp_prod.groupby(['value']).count().reset_index()
grp_prod_cou.rename(columns = {'value':'no_of_users'}, inplace=True)
grp_prod_cou.rename(columns = {'product_id':'product_count'}, inplace=True)
grp_prod_cou = grp_prod_cou.sort_index(ascending = False)
grp_prod_cou['product_per'] = grp_prod_cou['product_count']/grp_prod_cou['product_count'].sum() * 100
grp_prod_cou['aggregated_per'] = grp_prod_cou.product_per.cumsum()
grp_prod_cou = grp_prod_cou.reset_index(drop=True)
threshold_df_prod = grp_prod_cou.loc[grp_prod_cou['aggregated_per'] > 85]
threshold_df_prod = threshold_df_prod.reset_index(drop=True)
threshold_value_prod = threshold_df_prod.no_of_users.loc[threshold_df_prod['aggregated_per'] > 90]
threshold_value_prod = threshold_value_prod.reset_index(drop=True)
prod = grp_prod.loc[grp_prod['value'] > threshold_value_prod[0]]
prod = prod.reset_index(drop=True)
del prod['value']
print "products creted"

final_data = event_table.merge(cust,on='cust_id').merge(prod,on='product_id')
final_data.action_type.replace([3],[-1], inplace=True)

print "final data created"

del [cust, doc, grp_cust, grp_cust_cou, grp_prod, grp_prod_cou, prod, threshold_df_cust,
     threshold_df_prod, threshold_value_cust, threshold_value_prod, event_table]

final_data.to_csv('alstable_event.csv', sep = ',', index = False, mode = 'w')
print "csv written"

print dt.datetime.now() - start_time


###################################### EVENT Recommendations ###########################################


from pyspark import SparkContext
from pyspark.sql import SQLContext
from pyspark.mllib.recommendation import ALS

sc = SparkContext(appName="event_recommendations")
sqlContext = SQLContext(sc)
print "spark"
df = sqlContext.read.csv("/home/ubuntu/alstable_event.csv", header=True, sep = ',')
trans = pd.read_csv('/home/ubuntu/alstable_event.csv', index_col=None)
print "table read"

print "final model"
final_model = ALS.train(df, rank=16, seed=49247, iterations=10,lambda_= 0.1)
print "model created"

i = 1
import csv
for x in trans.cust_id.unique():
    recommendations = final_model.recommendProducts(x,10)
    ac = []
    for c in recommendations:
        rec_dict = {'cust_id':c[0],'recommended_product':c[1],'rating':c[2]}
        ac.append(rec_dict)
    if i == 1:
        openMode = 'w'
        keys = ac[0].keys()
    else :
        openMode = 'a'
    with open('/home/ubuntu/trans_rec.csv', openMode) as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        if i == 1:
            dict_writer.writeheader()
        dict_writer.writerows(ac)
    i = i+1

print "completed"

sc.stop()

print dt.datetime.now() - start_time
