import requests
import pandas as pd
import time, random
from datetime import date, timedelta
import numpy as np
import scipy.stats as ss

#API token from tradier (Authorization:Token)
TOKEN = open('tokens.txt').readline().split(':')[1].strip()

class OptionsCalc:

    def __init__(self, ticker):
        self.ticker = ticker #Stock Ticker
        self.expiration = None #Expiration date yyyy-mm-dd
        self.Otype = None #Option type
        self.strike = None #Strike price
        self.contract = None #Contract price
        self.datesUntilExp = None #List of dates until expiration
        self.sigma = None #Implied volatility
        self.rf = .0165 #Risk free rate

        #Sets the ask and description
        self.ask = self.setStockInfo()['ask']
        self.description = self.setStockInfo()['description']

    #Fetches the stock information, see https://documentation.tradier.com/brokerage-api/markets/get-quotes for more info
    def setStockInfo(self):
        response = requests.get('https://sandbox.tradier.com/v1/markets/quotes',
            params={'symbols': self.ticker},
            headers={'Authorization': TOKEN, 'Accept': 'application/json'})

        #Has to be a 200 status code
        try:
            response.raise_for_status()
        except Exception as e:
            print("-----Error in setStockInfo(): {}-----".format(e))

        quoteResponse = response.json()
        return quoteResponse['quotes']['quote']

    #Only returns the stock option expirations. See https://documentation.tradier.com/brokerage-api/markets/get-options-expirations for more info
    def getExpDates(self):
        response = requests.get('https://sandbox.tradier.com/v1/markets/options/expirations',
            params={'symbol': self.ticker, 'includeAllRoots': 'true', 'strikes': 'true'},
            headers={'Authorization': TOKEN, 'Accept': 'application/json'})

        #Has to be a 200 status code
        try:
            response.raise_for_status()
        except Exception as e:
            print("-----Error in getExpDates(): {}-----".format(e))

        expResponse = response.json()

        #Returns the dates for the selected stock
        return [k['date'] for k in expResponse['expirations']['expiration']]


    #Returns the option chain. See https://documentation.tradier.com/brokerage-api/markets/get-options-chains for more info
    def getOptionChain(self):
        response = requests.get('https://sandbox.tradier.com/v1/markets/options/chains',
            params={'symbol': self.ticker, 'expiration': self.expiration},
            headers={'Authorization': TOKEN, 'Accept': 'application/json'})

        #Has to be a 200 status code
        try:
            response.raise_for_status()
        except Exception as e:
            print("-----Error in getOptionChain(): {}-----".format(e))

        optionChainResponse = response.json()

        #For readability
        chain = []
        for k in optionChainResponse['options']['option']:
            if k['option_type'] == 'call' and self.Otype.strip('s') == 'call':
                callDict = {}
                callDict['strike'] = k['strike']
                callDict['bid'] = k['bid']
                callDict['mid'] = (k['bid'] + k['ask']) / 2
                callDict['ask'] = k['ask']

                chain.append(callDict)

            if k['option_type'] == 'put' and self.Otype.strip('s') == 'put':
                putDict = {}
                putDict['strike'] = k['strike']
                putDict['bid'] = k['bid']
                putDict['mid'] = (k['bid'] + k['ask']) / 2
                putDict['ask'] = k['ask']

                chain.append(putDict)


        df = pd.DataFrame(chain)
        df.set_index('strike', inplace=True)
        return df

    #Gets the date range for calculating time until expiration
    def setDateRange(self):

        sDate = date.today()  # start date
        y, m, d = self.expiration.split('-') # splits the user input
        eDate = date(int(y), int(m), int(d)) # end date
        delta = eDate - sDate # as timedelta

        #Sets a list of dates until expiration
        self.datesUntilExp = [str(sDate + timedelta(days=i)) for i in range(delta.days + 2)]

    #Gets Implied Vol. See website for params, greeks are optional and updated once per hour
    def setIV(self):
        response = requests.get('https://sandbox.tradier.com/v1/markets/options/chains',
            params={'symbol': self.ticker, 'expiration': self.expiration, 'greeks': True},
            headers={'Authorization': TOKEN, 'Accept': 'application/json'})

        #Has to be a 200 status code
        try:
            response.raise_for_status()
        except Exception as e:
            print("-----Error in setIV(): {}-----".format(e))

        impliedVolResponse = response.json()

        #Find the implied volatility for the selected stock
        iv = None
        for k in impliedVolResponse['options']['option']:
            if k['option_type'] == self.Otype.strip('s') and k['strike'] == self.strike:
                iv = k['greeks']['ask_iv']

        self.sigma = iv

    #Returns the payoff matrix as a dataframe
    def getPayoffMatrix(self):

        payoff = {}

        #Sets the the stock price 20 above and 20 below breakeven Edit for whatever you like
        self.ask += 20
        self.ask = round(int(self.ask))

        for y in range(1, 40):

            #Profit array
            profarr = []

            #Days until Expiration
            days = len(self.datesUntilExp)

            for x in range(days):

                #Takes in the length of daysUntilExp array / 365 to get time until exp for BSOPM
                T = self.timeCalc(days)

                #BSOPM
                c_BS = self.blackScholes(self.ask, self.strike, self.rf, self.sigma, T, self.Otype)

                #Calculates the profit by the original option price and the expected price by BSOPM
                profit = round((c_BS * 100) - (self.contract* 100), 2)
                profarr.append(profit)

                #Get closer to expiration
                days -= 1

            payoff[self.ask] = profarr

            #Subtracts the strike price by 1
            self.ask -= 1

        return pd.DataFrame(payoff, index=self.datesUntilExp).transpose()

    #For calculating breakeven price
    def getBreakEven(self):
        breakeven = None

        if self.Otype == 'calls':
            breakeven = self.strike + self.contract
        else:
            breakeven = self.strike - self.contract

        return breakeven

    #For calculating days till expiration helper
    def timeCalc(self, daysTill):
        return daysTill / 365

    #Black and Scholes helper
    def d1(self, S0, K, r, sigma, T):
        return (np.log(S0/K) + (r + sigma**2 / 2) * T)/(sigma * np.sqrt(T))

    def d2(self, S0, K, r, sigma, T):
        return (np.log(S0 / K) + (r - sigma**2 / 2) * T) / (sigma * np.sqrt(T))

    def blackScholes(self, S0, K, r, sigma, T, Otype):
        if Otype=="calls":
            return S0 * ss.norm.cdf(self.d1(S0, K, r, sigma, T)) - K * np.exp(-r * T) * ss.norm.cdf(self.d2(S0, K, r, sigma, T))
        else:
            return K * np.exp(-r * T) * ss.norm.cdf(-self.d2(S0, K, r, sigma, T)) - S0 * ss.norm.cdf(-self.d1(S0, K, r, sigma, T))
