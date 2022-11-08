# About Venus

此文档用来解释Venus的工作原理，以及我们如何利用`AccrueInterest`事件来追踪利率变化。

## Venus AccrueInterest Event

Venus的利率在以下5个操作时，会发生变化：
* `mint`: 存入token, 增发vToken；
* `redeem`: 取出token，销毁vToken；
* `borrow`: 借出token；
* `repayBorrow`: 还回token；
* `liquidateBorrow`: 清算；
以上操作还存在一些变体，比如`repayBorrowBehalf`，`repayAmount`，但是本质的操作是一样的。

当这些操作发生时，合约会首先调用