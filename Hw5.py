"""
Author: 
    Justin Moua CSC148 12/16/21
Program: "Single Category Inventory Model with plywood bundles simulation using simpy"
    - 1 t.u. = 1 hour
    - Stores work 24x7
    - 1 warehouse, 23 regular stores, 2 super store
    - stores send request to warehouse when restock point reached
    - stores stop taking orders when stockout is reached, and store waits for warehouse restock event before taking more orders
    - warehouse waits for restock interrupt from stores and then schedules restock pf for specific store
    - warehouse can restock multiple stores at once
    - Start model time = 0 (which is equivlant to 6am on monday)
    - End model time = 120 t.u.
"""


import simpy
import random
import numpy as np


class Store: # equivalent to HD class
    _arrivalInterval = (0, 0)
    _storeName = "none"
    _inventory = 0
    _reorderPoint = 0
    _stockoutCount = 0
    _restockCount = 0
    _orderSizeInterval = (0, 0)
    _listOfOrderSizes = [-1]
    _maxInventory = -1
    _isRestockingScheduled = False
    _hasRestockPointReached = False
    _isStockout = False

    _restockProcessEvent = -1 # The shared event that is used to interrupt the warehouse restock process function
    _restockCompleteEvent = -1
    _resumeDoProcessEvent = -1


    _env = -1

    def __init__(self, name, inventory, reorderPoint, arrivalInterval, orderSizeInterval, restockProcessEvent):
        self._storeName = name
        self._inventory = inventory
        self._reorderPoint = reorderPoint
        self._arrivalInterval = arrivalInterval
        self._orderSizeInterval = orderSizeInterval
        self._restockProcessEvent = restockProcessEvent
        self._listOfOrderSizes = list()

        self._maxInventory = inventory

    def scheduleOrderEvent(self, env):
        """ Create HD process functions"""
        if env != -1 and self._restockCompleteEvent != -1:
            errorString = "ERROR: doOrder for {} has already been added to the simulation"
            print(errorString.format(self._storeName))

        self._env = env
        # shared events
        self._resumeDoProcessEvent = env.process(self.doOrderPf(env))
        self._restockCompleteEvent = env.process(self.restockListenerPf(env))

    def restockListenerPf(self, env):
        """Handles event when W completes restock for store; if store is in stockout, resume doOrderPf() by interrupting doOrderPf()"""
        while True:
            try:
                yield env.timeout(10)  # need to yield or else nothing else can run
            except simpy.Interrupt as interruptMsg:
                if self._isStockout:
                    self._resumeDoProcessEvent.interrupt()  # restart HD doOrderPf()
                self.restockCompleted()
                print("HD  {0}  completed re-stocking, resuming w. I(t) =  {1}  at time   {2}"
                      .format(self._storeName[-1], self._inventory, env.now)
                )

    def doOrderPf(self, env):
        """Handles orders for stores untill stockout; on stockout loop yield untill restock completes."""
        print("Starting doOrder() for {0} at time {1} with Init. Inventory = {2}, RP value = {3}"
              .format(self._storeName, env.now, self._inventory, self._reorderPoint)
        )
        while True:
            randomWaitTimeBeforeOrderArrives = int(np.random.uniform(
                self._arrivalInterval[0],
                self._arrivalInterval[1]))

            yield env.timeout(randomWaitTimeBeforeOrderArrives)

            orderSize = int(np.random.uniform(
                self._orderSizeInterval[0],
                self._orderSizeInterval[1]
            ))

            """ 
            Don't need to worry about case where doOrderPf() gets stuck in loop due to both doOrderPf() and restockListenerPf()
            because simpy executes process functions sequentially, even if both pf are running at the same model time. 
            """
            if ((self._inventory - orderSize) < 0): # if Stock out has occurred, terminate process function
                self._stockoutCount = self._stockoutCount + 1
                try:
                    self._isStockout = True
                    print("%%% Stockout occurred for HD {0} at time {1}".format(self._storeName, env.now))
                    while True:
                        yield env.timeout(10)  # need to yield or else nothing else can run
                except simpy.Interrupt as interruptMsg:
                    continue
            elif (self._inventory - orderSize) >= 0: # handle orders
                self._inventory = self._inventory - orderSize
                list.append(self._listOfOrderSizes, orderSize)

                procStr = "{0}  inventory level is  {1}  at time  {2}"
                print(procStr.format(self._storeName, self._inventory, env.now))

                # Tell warehouse to schedule a reOrder event when inventory go below reorder point
                if self._inventory < self._reorderPoint and not self._hasRestockPointReached:
                    print("!!! HD  {0}  is interrupting warehouse w at time  {1}".format(self._storeName[2:], env.now))
                    self._hasRestockPointReached = True
                    # send interrupt message with store number to Warehouse dispatcher() process function
                    self._restockProcessEvent.interrupt(self._storeName)
            else:
                print("ERROR: Code should not reach here: line 75")
                exit();

    def restockCompleted(self):
        self._restockCount = self._restockCount + 1
        self._isRestockingScheduled = False
        self._hasRestockPointReached = False
        self._isStockout = False

    def restockScheduled(self):
        self._isRestockingScheduled = True

    def isRestockingScheduled(self):
        return self.isRestockingScheduled()

    def getName(self):
        return self._storeName
    def getCurrentInventory(self):
        return self._inventory
    def getMaxInventory(self):
        return self._maxInventory
    def getListOfOrderSizes(self):
        return self._listOfOrderSizes
    def isRestockingScheduled(self):
        return self._isRestockingScheduled
    def getStockoutCount(self):
        return self._stockoutCount
    def getRestockCount(self):
        return self._restockCount
    def getRestockCompleteEvent(self):
        return self._restockCompleteEvent
    def addInventoryToStore(self, value):
        if value + self._inventory > self._maxInventory:
            print("ERROR inventory has gone over max inventory {0}".format(self._storeName))
            exit(0)
        self._inventory = self._inventory + value

class Warehouse:
    _listOfStores = -1
    _name = ""
    _restockProcessFunction = -1
    _restockTimeInterval = (0, 0)

    def __init__(self, name, env):
        self._name = name
        self._restockTimeInterval = (2, 6)  # up to but not including the last number
        self._restockProcessFunction = env.process(self.dispatcher(env))
        self.initInv(env)

    def initInv(self, env):
        END_RANGE = 26   # range does not include limit value
        str = "Running __init__ for {0} at time {1} // Random Seed = {2}"
        print(str.format(self._name, env.now, RAND_SEED))
        str = "Creating {0} HD stores"
        print(str.format(END_RANGE - 1))
        self._listOfStores = [self._initStore(x, env) for x in range(1, END_RANGE)]

    def getListOfStore(self):
        return self._listOfStores

    def _initStore(self, index, env):
        name = "HD" + str(index)
        defaultInventory = 200
        defaultReorderPoint = 50
        defaultArrivalInterval = (1, 3) # up to but not including the last number
        defaultOrderSizeInterval = (10, 41) # up to but not including the last number


        if index == 1 or index == 20:
            defaultInventory = 400

        initStr = "Running {0} __init__ fn at time {1}; Init. Inventory = {2}, RP value = {3}"
        #print(initStr.format(name, env.now, defaultInventory, defaultReorderPoint))

        return Store(
            name,
            defaultInventory,
            defaultReorderPoint,
            defaultArrivalInterval,
            defaultOrderSizeInterval,
            self._restockProcessFunction
        )

    def scheduleRestockForStore(self, storeIndex, storeNum, env):
        """Schedule restock process function for specified store"""
        store = self._listOfStores[storeIndex]
        store.restockScheduled()  # turns isRestockScheduled var in store to true
        env.process(self.restockStorePf(env, store))
        print("Start scheduling & delivering restock to HD  {0} at time  {1}".format(storeNum, env.now))

    def restockStorePf(self, env, store):
        """Restock implementation details for restocking specific store"""
        restockTime = int(np.random.uniform(
            self._restockTimeInterval[0],
            self._restockTimeInterval[1]
        ))

        yield env.timeout(restockTime)

        inventoryToAdd = store.getMaxInventory() - store.getCurrentInventory()
        store.addInventoryToStore(inventoryToAdd)
        store.getRestockCompleteEvent().interrupt()

    def dispatcher(self, env):
        """Handles HD requests for restocking"""
        while True:
            try:
                yield env.timeout(10)  # need to yield or else nothing else can run
            except simpy.Interrupt as interruptMsg:
                cause = interruptMsg.cause  # parse interrupt message by getting only the store #, example format of msg = "HD1"
                storeNum = int(cause[2:])
                storeIndexInList = int(cause[2:]) - 1  #need to -1 because first store is at 1, but list starts at 0
                self.scheduleRestockForStore(storeIndexInList, storeNum, env)  #schuedule a process function to restock store

def periodicReportForScheduledRestocksPf(env, timeInterval, listOfStores):
    while True:
        yield env.timeout(timeInterval)
        listOfStoresThatHaveScheduledRestock = []
        for store in listOfStores:
            if store.isRestockingScheduled():
                list.append(listOfStoresThatHaveScheduledRestock, store.getName())
        print("RPT:: The HDKs with pending restocks at time {0} :: {1}".format(env.now, listOfStoresThatHaveScheduledRestock))


RESTOCK_REPORTING_INTERVAL = 5 # 5 t.u.
RAND_SEED = 123456
END_TIME = 120
def main():
    env = simpy.Environment()
    np.random.seed(RAND_SEED)

    warehouse = Warehouse("WH1", env)
    listOfStores = warehouse.getListOfStore()
    # add periodic reporting process function to simulation
    env.process(periodicReportForScheduledRestocksPf(env, RESTOCK_REPORTING_INTERVAL, listOfStores))
    # add doOrder process functions of each store to simulation
    for store in listOfStores:
        store.scheduleOrderEvent(env)

    env.run(END_TIME)

    #ending code
    endStr = "Finished run at model time    {0}"
    print()
    print(endStr.format(env.now))

    listOfStockouts = []
    totalStockouts = 0
    totalRestocks = 0
    for store in listOfStores:
        listOfStockouts.append(store.getStockoutCount())
        totalStockouts = totalStockouts + store.getStockoutCount()
        totalRestocks = totalRestocks + store.getRestockCount()

    print("Total number of stockouts, by HD number {0}".format(listOfStockouts))
    print("Grand total number of stockouts over all HDK:  {0}".format(totalStockouts))
    print("Grand total number of restocks over all HDK:  {0}".format(totalRestocks))

if __name__ == "__main__":
    main()