from numpy import double
import websocket, json , talib , time
import pandas as pd

token = 'YSlL7MkIy8mM90q'
app_id = 24354
apiUrl = "wss://ws.binaryws.com/websockets/v3?app_id="+str(app_id)
req_json = {
  "ping": 1
}
steps = 0
session_start_balance = 0
profit_target = 0
wins_loss = ""
stake_steps = [0.5 , 0.58 , 1.24 , 2.6 , 5.71 , 12.29]
stake = stake_steps[steps]
open_contract = 0

def buy(direction , duration = 1 ,ws2 = websocket.WebSocket(), martingale = False):
    ws2.connect(apiUrl)
    data = json.dumps({'authorize': token})
    ws2.send(data)

    global steps
    global stake
    global profit_target
    
    while True :
        message = json.loads(ws2.recv())
        ##print("message conatins")
        #print(message)
        #
        if 'error' in message.keys():
            print('Error Happened: %s' % message)
            # With Websockets we can not control the order things are processed in so we need
            # to ensure that we have received a response to authorize before we continue.
        elif message["msg_type"] == 'authorize':
            balance = message["authorize"]["balance"]
            #stake = round((float(balance*0.1))*steps,2)
            stake = balance // 25
            print("Authorized OK, so now buy Contract")
            if stake <= 100:
                json_data1 = json.dumps({"buy": 1, "subscribe": 1,"price":100, "parameters": {
                                        "amount": stake , "basis": "stake", "contract_type": f"{direction}", "currency": "USD", "duration": duration, "duration_unit": "m", "symbol": "R_100"}})
            else:
                json_data1 = json.dumps({"buy": 1, "subscribe": 1,"price":100, "parameters": {
                                        "amount": 100 , "basis": "stake", "contract_type": f"{direction}", "currency": "USD", "duration": duration, "duration_unit": "m", "symbol": "R_100"}})
 
            ws2.send(json_data1)
            # Our buy request was successful let's print the results.
        elif message["msg_type"] == 'buy':
            print("contract Id  %s " %  message["buy"]["contract_id"] )
            print("Details %s " % message["buy"]["longcode"] )

        elif message["msg_type"] == 'proposal_open_contract':
            isSold = bool(message["proposal_open_contract"]["is_sold"])
                # If `isSold` is true it means our contract has finished and we can see if we won or not.
            if isSold:
                print("Contract %s " % message["proposal_open_contract"]["status"] )
                print("Profit %s " %  message["proposal_open_contract"]["profit"] )
                if (message["proposal_open_contract"]["status"] == 'won'):# or stake > 55:
                    steps = 0
                elif martingale and message["proposal_open_contract"]["status"] == 'lost' :
                    steps = steps + 1
                ws2.close()
                if steps > 3 :
                    time.sleep(120)
                    if steps > len(stake_steps):
                        steps = 0

                profit_target = profit_target + int(message["proposal_open_contract"]["profit"] )
                break
            else:  # We can track the status of our contract as updates to the spot price occur.
                currentSpot = message["proposal_open_contract"]["current_spot"]
                entrySpot = 0
                try:
                    if message["proposal_open_contract"]["entry_tick"] != None:
                        entrySpot = message["proposal_open_contract"]["entry_tick"]
                except:
                    pass
                print ("Entry spot %s" % entrySpot )
                print ("Current spot %s" % currentSpot )
                print ("Difference %s" % (currentSpot - entrySpot) )
                print ("Profit %s " %  message["proposal_open_contract"]["profit"] )
        else:
            print(f"error happened === {message}")



def get_stream(ws10 = websocket.WebSocket()):
    ws10.connect(apiUrl)
    json_data = json.dumps({
     "ticks_history": "R_100",
     "adjust_start_time": 1,
     "count": 100,
     "end": "latest",
     "start":1,
     "style": "candles"
     })
    ws10.send(json_data)
    rec = json.loads(ws10.recv())
    try:
        rec = pd.DataFrame(rec["candles"])
        return rec
    except:
        print (f"error happned while retreiving stream ::: {rec}")


def analize(df):

    df['ema'] = talib.TRIMA(df['close'],timeperiod = 50)
    df = df.dropna(axis=0)

    win = df.tail(n=4)
    max_close = float(win['close'].max())
    min_close = float(win['close'].min())
    prev_close = float(win.iloc[[-2]]['close'])
    ema = float(win.iloc[[1]]['ema'])


    if prev_close == min_close and prev_close > ema :
        acc = 1
    elif prev_close == max_close and prev_close < ema:
        acc = 2 
    
    else:
        acc = 0
    

    return acc


def on_open(ws):
    try:
        data = json.dumps(req_json)
        ws.send(data)
    except:
        print("couldnt open connection")

def on_message(ws, message):
    try:
        global steps
        data = json.loads(message)
        #print('Data: %s' % message) # Uncomment this line to see all response data.
        if 'error' in data.keys():
            print('Error Happened: %s' % message)
        while True :
            try:
                acc = analize(get_stream())
                
                if  acc == 1:
                
                    print('buying call option')
                    buy("CALL")
                            
                elif   acc == 2:
                    print('buying put option')
                    buy("PUT")

                # elif   X_test[-1] == 2 and X_test[-2] == 2 :
                #     print('buying call option')
                #     buy("CALL")
                
                # elif   X_test[-1] == 1 and X_test[-2] == 1 :
                #     print('buying put option')
                #     buy("PUT")


            except Exception as e:
                print (f"error : {data}")
                print(e)
                pass
    except Exception as e:
        print(e)
            
if __name__ == "__main__":
    ws = websocket.WebSocketApp(apiUrl, on_message=on_message, on_open=on_open)
    ws.run_forever()
