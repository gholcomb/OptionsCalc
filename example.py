#Options command line example
#See more at https://documentation.tradier.com/

from options import OptionsCalc as OC
import pandas as pd

if __name__ == "__main__":
    print("----OPTIONS CALC----")
    stock = OC(input('Which stock ticker would you like to check? \n'))
    print('----------------')

    print('Price: ' + str(stock.ask))
    print('Description: ' + stock.description)
    expDecision = input('Would you like to see the expirations? \n').lower()

    #If the user already knows the expiration date... pass
    if expDecision == 'yes':
        #Prints newline expiration dates for the CLI
        print('EXPIRATIONS: \n')
        for date in stock.getExpDates(): print(date)
    else:
        pass

    stock.expiration = input('Select the expiration date and see the option chain: \n')
    stock.Otype = input('Would you like to see puts or calls? \n').lower()

    with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified
        print(stock.getOptionChain())

    stock.strike = float(input('Which strike price would you like to see? \n'))
    stock.contract = float(input('Which select the contract price: \n'))

    #Sets the list of dates until expiration
    stock.setDateRange()

    #Sets the implied volatility
    stock.setIV()

    print('\n --- Stock Price: ' + str(stock.ask) + ' ---\n')
    print('\n --- Contract Price: ' + str(stock.contract) + ' ---\n')
    print('\n --- Implied Volatility: ' + str(stock.sigma) + ' ---\n')
    print('\n --- Breakeven: ' + str(stock.getBreakEven()) + ' ---\n')

    print(stock.getPayoffMatrix())
