import pandas as pd
import tkinter
import tkinter.ttk

df = pd.read_csv('output.csv', index_col=0)



#
results = ['{:^8}'.format(str(df['Results'][x])) for x in df.index.tolist()]
names = ['{:^8}'.format(x) for x in df.index]
print(results)
print(names)
# result = tkinter.ttk.Label(results_frame, text = df.T)
# result.place(relx=0.5, rely=0.21, anchor=CENTER)