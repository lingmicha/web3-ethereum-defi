# MasterChef Staking 

[MasterChef合约用来管理质押LP Token，获取质押奖励。
每个DEX会将MasterChef做一定的修改，所以要引用不同的abi，此处也一并将引用出处总结一下。
]()
## MasterChef
- 提供向某一个pool 提供Liquidity 获得 LP-Token， LP Token可以获得Pool Trading Fee分成 
- Staking LP Token去MasterChef合约，获得Cake/Sushi reward
- MasterChef是一个合约管理不同的流动性池（Liquidity Pool), 使用pid来引用不同的池子。pid没有合约的查询方式，需要提前罗列。

### Sushiswap MasterChef
合约文档： https://docs.sushi.com/docs/Developers/Sushiswap/MasterChef

### Pancake V2 MasterChef
V2合约地址：`0xa5f8C5Dbd5F286960b9d90548680aE5ebFf07652`

BSCSCAN: https://bscscan.com/address/0xa5f8C5Dbd5F286960b9d90548680aE5ebFf07652

pid文档: https://github.com/pancakeswap/pancake-frontend/tree/400fde5df71d14e24e2a9e87fe11788619cbb853/packages/farms/constants

## MasterChef 收益计算

以下参数并不是实际的合约参数：

    AccumulatedRewardsPerShare：相当于lending中的borrowIndex，即从初始区块累积到当前区块的单位LP token可以获得的Reward。
    StakerTokenAmount：质押的LP Token数量。
    RewardDebt：上一次存取操作时，记录下的 RewardDebt = StakerTokenAmount * AccumulatedRewardsPerShare的金额。

    StakerRewards = StakerTokenAmount * (AccumulatedRewardsPerShare_2 - AccumulatedRewardsPerShare_1)
    PendingStakerRewards = StakerTokenAmount * AccumulatedRewardsPerShare - rewardDebt

备注：
1. StakerRewards 是从时间1-时间2总的Rewards收益，不论该收益有没有被领取，也可能部分领取。只要质押的LP Token数量不变，就可以这样计算。
2. RewardDebt是用来计算未领取奖励（pendingRewards)的简便方法。
3. 收益计算的参考文档：https://dev.to/heymarkkop/understanding-sushiswaps-masterchef-staking-rewards-1m6f

## MasterChef 收益计算举例：Pancakeswap

    只读合约函数：contract.functions.poolInfo(pid).call()
    返回： accCakePerShare 即 AccumulatedRewardsPerShare
    
    只读合约函数：contract.functions.userInfo(pid, account).call()
    返回： amount： LP Token数量， rewardDebt即RewardDebt

    简易的pendingReward读取，不用计算：
    pendingReward = contract.functions.pendingCake(pid, account).call()
    assert pendingReward == (accCakePerShare * amount - rewardDebt) (需要考虑mantissa)
    
    但是当中间有若干次存取操作时，使用RewardDebt可能更灵活。

## 存取操作产生的影响
- 用户存取操作时，该池子里的pendingReward会被发放给用户(transfer操作),并且更新rewardDebt和accCakePerShare（针对pancake）
- 用户Harvest时，相当于做了一个deposit，量为0


## How to calcualte APR for a masterchef contract

参考文档： https://ethereum.stackexchange.com/questions/101662/how-to-calculate-apr-from-a-masterchef-contract-pool


