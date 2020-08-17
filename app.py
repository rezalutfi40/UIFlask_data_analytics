from flask import Flask, render_template
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import base64 

app = Flask(__name__)

# membaca csv dan menyimpan pada objek playstore
playstore = pd.read_csv('data/googleplaystore.csv')

# menghilangkan nilai yang duplikat pada kolom App
playstore.drop_duplicates(subset='App',keep='first')

# menghilangkan bari ke 10472 karena memiliki format yang berbeda dari yang lainnya 
playstore.drop([10472], inplace=True)

# mengubah tipe data kolom Category menjadi kategorikal
playstore.Category = playstore.Category.astype('category') 

# mengubah format kolom Installs dengan membuang koma (,) dan plus (+) dan mengubahnya menjadi numerik
playstore.Installs = playstore.Installs.apply(lambda x: x.replace(',',''))
playstore.Installs = playstore.Installs.apply(lambda x: x.replace('+',''))
playstore.Installs = pd.to_numeric(playstore.Installs)

# membuang nilai 'Varies with device' pada kolom Size menjadi nan menggunakan numpy
playstore.Size.replace('Varies with device',np.nan, inplace=True)

# filtering nilai yang mengandung k, M dan $ lalu diubah kedalam tipe data float. setelah itu, nilai yang mengandung k dan M masing-masing dikalikan dengan 10^3 dan 10^6 
playstore.Size = (playstore.Size.replace(r'[kM]+$','',regex=True).astype(float)*playstore.Size.str.extract(r'[\d\.]+([kM]+)',expand=False).fillna(1).replace(['k','M'],[10**3,10**6]).astype(int))

# menggabungkan kolom Category dan Size, lalu di hitung rata-rata pada kolom Size
playstore.Size.fillna(playstore.groupby('Category')['Size'].transform('mean'),inplace=True)

# menghilangkan nilai $ pada kolom Price, lalu diubah tipe datanya menjadi float
playstore['Price'] = playstore['Price'].apply(lambda x: x.replace('$',''))
playstore.Price = playstore.Price.astype('float64')

# mengubah tipe data kolom Reviews, Size dan Installs menjadi integer
playstore[['Reviews','Size','Installs']] = playstore[['Reviews','Size','Installs']].astype('int64')

@app.route("/")
def index():
    # menduplikat dataframe playstore kedalam objek df2
    df2 = playstore.copy()

    # melakukan aggregasi pada kolom Category dan membuat kolom 'Jumlah'
    top_category = pd.crosstab(
    index=df2['Category'],
    columns='Jumlah'
    ).sort_values(by='Jumlah',ascending=False).reset_index()

    # membuat objek stats yang berisikan informasi detail mengenai most_categories dan total in market
    stats = {
    'most_categories':top_category.iloc[0,0],
    'total':top_category.iloc[0,1],
    'rev_table':df2.groupby(['Category','App']).agg({'Reviews':'sum','Rating':'mean'}).sort_values(by=['Reviews','Category'],ascending=False).head(10).to_html(classes=['table thead-light table-striped table-bordered table-hover table-sm'])
    }

    # melakukan aggregasi untuk membuat bar chart pada kolom Category dan Total 
    cat_order = pd.crosstab(
    index=df2['Category'],
    columns='Total'
    ).sort_values(by='Total', ascending=False).reset_index().head()

    X = cat_order['Category']  # menjadikan kolom Category sebagai sumbu X 
    Y = cat_order['Total'] # menjadikan kolom Total sebagai sumbu Y

    my_colors = 'rgbkymc' # pemilihan warna pada bar chart 

    fig = plt.figure(figsize=(8,3),dpi=300) # mengatur ukuran gambar 
    fig.add_subplot()
    plt.barh(X,Y,color=my_colors)
    plt.savefig('cat_order.png',bbox_inches='tight')
    figfile = BytesIO()
    plt.savefig(figfile,format='png')
    figfile.seek(0)
    figdata_png = base64.b64encode(figfile.getvalue())
    result = str(figdata_png)[2:-1]

    # membuat scatter plot pada kolom Reviews dan Rating 
    A = df2['Reviews'].values
    B = df2['Rating'].values
    area = playstore['Installs'].values/10000000
    fig = plt.figure(figsize=(5,5))
    fig.add_subplot()
    
    plt.scatter(x=A, y=B, s=area, alpha=0.3)
    plt.xlabel('Reviews')
    plt.ylabel('Rating')
    plt.savefig('rev_rat.png',bbox_inches="tight")
    
    figfile = BytesIO()
    plt.savefig(figfile, format='png')
    figfile.seek(0)
    figdata_png = base64.b64encode(figfile.getvalue())
    result2 = str(figdata_png)[2:-1]

    C = (df2['Size']/1000000).values
    fig = plt.figure(figsize=(5,5))
    fig.add_subplot()
    plt.hist(C,bins=100,density=True, alpha=0.75)
    plt.xlabel('Size')
    plt.ylabel('Frequency')
    plt.savefig('hist_size.png',bbox_inches="tight")
    
    figfile = BytesIO()
    plt.savefig(figfile, format='png')
    figdata_png = base64.b64encode(figfile.getvalue())
    result3 = str(figdata_png)[2:-1]

    playstore_pvt = playstore.pivot_table(
                        index='Category',
                        columns='Type',
                        values='Price')  
    playstore_pvt.fillna(0).sort_values(by='Paid', ascending=False).drop('Free', axis=1).head(5)\
    .plot.pie(subplots=True)

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(aspect="equal"))

    kategori = ["171 FINANCE",
          "124 LIFESTYLE",
          "101 EVENTS",
          "13 BUSINESS",
          "13 MEDICAL"]

    data = [float(x.split()[0]) for x in kategori]
    ingredients = [x.split()[-1] for x in kategori]


    def func(pct, allvals):
        absolute = int(pct/100.*np.sum(allvals))
        return "{:.1f}%\n($ {:d})".format(pct, absolute)


    wedges, texts, autotexts = ax.pie(data, autopct=lambda pct: func(pct, data),
                                  textprops=dict(color="w"))

    ax.legend(wedges, ingredients,
          title="Category",
          loc="center left",
          bbox_to_anchor=(0, 0, 0, 0))

    plt.setp(autotexts, size=12, weight="bold")

    ax.set_title("Top 5 PAID Categories", fontsize=18)

    plt.savefig('piechart.png', bbox_inches="tight")

    figfile = BytesIO()
    plt.savefig(figfile, format='png')
    figfile.seek(0)
    figdata_png = base64.b64encode(figfile.getvalue())
    result4 = str(figdata_png)[2:-1]

    return render_template('index.html', stats=stats, result=result, result2=result2, result3=result2, result4=result4)

if __name__=='__main__':
    app.run(debug=True)







