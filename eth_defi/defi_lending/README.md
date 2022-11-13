# About Compound V2

此文档用来解释Compound V2的工作原理，以及我们如何利用`AccrueInterest`事件来追踪利率变化。
这一原理应该适用于fork Compound V2的所有协议，包括现在支持的venus和WePiggy。
此处我们以Venus为例。

## Venus Market
目前的Venus Market:

|Token|Token|Token|Token|
|-----|-----|-----|-----|
|SXP|USDC|USDT|BUSD|
|XVS|BTC|ETH|LTC|
|XRP|WBNB|BCH|DOT|
|LINK|DAI|FIL|BETH|
|CAN|ADA|DOGE|MATIC|
|CAKE|AAVE|TUSD|TRX|

## WePiggy Market
WePiggy Market:

|Token|Token|Token|Token|
|-----|-----|-----|-----|
|WBNB|USDC|USDT|BUSD|
|DAI|ETH|BTCB|LTC|
|XRP|WBNB|BCH|DOT|
|CAKE|ADA|FIL|LTC|

## Venus AccrueInterest Event

Venus的利率在以下5个操作时，会发生变化：
* `mint`: 存入token, 增发vToken；
* `redeem`: 取出token，销毁vToken；
* `borrow`: 借出token；
* `repayBorrow`: 还回token；
* `liquidateBorrow`: 清算；
以上操作还存在一些变体，比如`repayBorrowBehalf`，`repayAmount`，但是本质的操作是一样的。

当这些操作发生时，合约会首先调用`accrueInterest() `函数计算累计的利息，再函数的最后，会触发event:

`emit AccrueInterest(cashPrior, interestAccumulated, borrowIndexNew, totalBorrowsNew)` 

我们会监控`AccrueInterest Event`来实时的跟踪利率变化。

## Venus 的利率模型

Venus目前有2种在用的利率模型，`WhitePaperInterestModel`和`JumpInterestModel`。
两者主要的差别是后者引入了`kink`的概念，在利用率超过某个阈值（`kink`）时，利率会以一个更陡峭的斜率上升。

目前只有`XVS`和`CAN`两个市场是使用`WhitePaperInterestModel`。

利率的计算方式如下：

    utilizationRate = 
        totalBorrows / (Cash + totalBorrows - totalReserves)
    
    borrowRatePerBlock = 
    (1) WhitePaper Model:
        utilizationRate * multiplierPerBlock + baseRatePerBlock

    (2) Jump Model
        utilizationRate < kink: utilizationRate * multiplierPerBlock + baseRatePerBlock
        utilizationRate >= kink: normalRate + excessRate
            normalRate = kink * multiplierPerBlock + baseRatePerBlock
            excessRate = (utilizationRate - kink) * jumpMultiplierPerBlock

    supplyRatePerBlock:
        utilizationRate * borrowRatePerBlock * ( 1 - reserveFactor )

## Venus的链上函数及概念
* `totalSupply`:
  * 调用函数：`contract.functions.totalSupply().call()`
  * 解读：获取`VToken Supply`, 只有mint/redeem时，才会增加、减少VToken供给。
  * 需要乘以 `exchangeRate` 得到总共存入合约的Token数量。
  * 注意：exchangeRateStored是截止上一次操作后的汇率，两个event之间保持不变，而exchangeRateCurrent是每个区块变化，根据最新的区块去累积利息得到新的汇率。
* `totalBorrows`:   
  * 调用函数：`contract.functions.totalBorrows().call()`
  * 解读：获取总共借出的Token数量。没有操作时不会增加，有操作时，会累积利息计算得到新的totalBorrows。 
  * `totalBorrowsCurrent`: 不同于`totalBorrows`每个区块都会将未累积的利息也包含后返回，故每个区块都会增加。
* `totalReserves`:  
  * 调用函数：`contract.functions.totalReserves().call()`
  * 解读：总的协议分红，或者说借贷利润中分给协议的部分。只有操作时才变更。
* `Cash`: 
  * 调用函数：`contract.functions.getCash().call()`
  * Cash是只有操作的时候才会累积的 
  * `Cash = totalSupply - totalBorrows + totalReserves`
  * totalReserves平时是Cash的方式存在，但是协议方可以随时提取转走
* `borrowIndex`:
  * 调用函数：`contract.functions.borrowIndex().call()`
  * 解读：方便计算利息的index， 利息计算方式为：amount * borrowIndex(现在）/ borrowIndex(存入时）
  * 只有操作时才会变动数值。

我们在计算利率时，用到的是每个`AccrueInterest Event`发生的区块的totalBorrows、Cash、totalReserves。
