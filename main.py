import asyncio
import aiohttp
import random
from better_automation.twitter import (
    Account as TwitterAccount,
    Client as TwitterClient,
    errors as twitter_errors,
)
from better_automation.utils import proxy_session

accounts = TwitterAccount.from_file("twitter_auth_tokens.txt")
import concurrent.futures

usernames = []
with open("usernames.txt", "r") as file:
    for username in file:
        username = username.strip()
        usernames.append(username)

tweets = []
with open("tweet_text.txt", "r") as file:
    for tweet in file:
        tweet = tweet.strip()
        tweets.append(tweet)

tweet_ids = []
with open("tweet_ids.txt", "r") as file:
    for tweet_id in file:
        tweet_id = tweet_id.strip()
        tweet_ids.append(tweet_id)

comment_texts = []
with open("comment_text.txt", "r") as file:
    for comment_text in file:
        comment_text = comment_text.strip()
        comment_texts.append(comment_text)

proxies = []
with open("proxies.txt", "r") as file:
    for proxy in file:
        proxy = proxy.strip()
        proxies.append(proxy)


print(
    f"Загружено {len(accounts)} аккаунтов. \
{len(usernames)} имен. \
{len(tweets)} текстов твитов. \
{len(tweet_ids)} tweet id. \
{len(comment_texts)} текста комментариев. \
{len(proxies)} прокси\n"
)
choice = input(
    """Подписка по имени: 1
Подписки между аккаунтами: 2
Твиты: 3
Ретвиты по id: 4
Комментарии по id: 5
Введите число: """
)


async def follow(account, usernames, proxy, semaphore):
    async with semaphore:
        for username in usernames:
            async with proxy_session(proxy) as session:
                twitter = TwitterClient(account, session)
                try:
                    user = await twitter.request_user_data(username)
                    print(
                        f"{account} подписался на {username}: {await twitter.follow(user.id)}"
                    )

                except twitter_errors.HTTPException as exc:
                    print(
                        f"Не удалось выполнить запрос. Статус аккаунта: {account.status.value}"
                    )
                    raise exc


async def follow_between_accounts(
    account, accounts, min_subs_count, max_subs_count, proxy, semaphore
):
    async with semaphore:

        async def subscribe(account, subscriber):
            async with proxy_session(proxy) as session:
                subscriber_twitter = TwitterClient(
                    TwitterAccount(subscriber.auth_token), session
                )
                account_twitter = TwitterClient(
                    TwitterAccount(account.auth_token), session
                )
                subscriber_username = await subscriber_twitter._request_username()
                subscriber_data = await subscriber_twitter.request_user_data(
                    subscriber_username
                )
                print(
                    f"{account} подписался на {subscriber_username}: {await account_twitter.follow(subscriber_data.id)}"
                )

        def count_followers(account, subscribers):
            return len(subscribers[account])

        subscribers = {account: [] for account in accounts}

        num_subscriptions = random.randint(min_subs_count, max_subs_count)
        local_accounts = accounts[:]

        if account in local_accounts:
            local_accounts.remove(account)

        selected_accounts = random.sample(local_accounts, num_subscriptions)

        for subscriber in selected_accounts:
            await subscribe(account, subscriber)
            subscribers[account].append(subscriber)

        num_followers = count_followers(account, subscribers)
        print(f"{account} имеет {num_followers} подписчиков")


async def do_tweet(account, tweet_text, proxy, semaphore):
    async with semaphore:
        async with proxy_session(proxy) as session:
            twitter = TwitterClient(account, session)

            print("account:", account, "tweet text:", tweet_text)
            tweet_id = await twitter.tweet(tweet_text)
            print(f"Tweet id: {tweet_id}")


async def do_retweet(account, tweet_id, proxy, semaphore):
    async with semaphore:
        async with proxy_session(proxy) as session:
            twitter = TwitterClient(account, session)
            print("account:", account, "tweet id:", tweet_id)
            print(
                f"Tweet {tweet_id} is retweeted. Tweet id: {await twitter.repost(tweet_id)}"
            )


async def do_comment(account, tweet_id, comment_text, proxy, semaphore):
    async with semaphore:
        async with proxy_session(proxy) as session:
            twitter = TwitterClient(account, session)
            print("account:", account, "tweet id:", tweet_id)
            print(
                f"Tweet {tweet_id} is replied. Reply id: {await twitter.reply(tweet_id, comment_text)}"
            )


async def main(usernames, accounts, proxies):
    semaphore = asyncio.Semaphore(1)
    tasks = []
    match choice:
        case "1":
            for account, proxy in zip(accounts, proxies):
                task = asyncio.create_task(follow(account, usernames, proxy, semaphore))
                tasks.append(task)
            await asyncio.gather(*tasks)
        case "2":
            min_subs_count = int(
                input("Введите минимальное количество подписчиков (например 3): ")
            )
            max_subs_count = int(
                input("Введите максимальное количество подписчиков (например 5): ")
            )
            for account, proxy in zip(accounts, proxies):
                task = asyncio.create_task(
                    follow_between_accounts(
                        account,
                        accounts,
                        min_subs_count,
                        max_subs_count,
                        proxy,
                        semaphore,
                    )
                )
                tasks.append(task)
            await asyncio.gather(*tasks)
        case "3":
            for account, tweet, proxy in zip(accounts, tweets, proxies):
                task = asyncio.create_task(do_tweet(account, tweet, proxy, semaphore))
                tasks.append(task)
            await asyncio.gather(*tasks)
        case "4":
            for account, tweet_id, proxy in zip(accounts, tweet_ids, proxies):
                task = asyncio.create_task(
                    do_retweet(account, tweet_id, proxy, semaphore)
                )
                tasks.append(task)
            await asyncio.gather(*tasks)
        case "5":
            for account, tweet_id, comment_text, proxy in zip(
                accounts, tweet_ids, comment_texts, proxies
            ):
                task = asyncio.create_task(
                    do_comment(account, tweet_id, comment_text, proxy, semaphore)
                )
                tasks.append(task)
            await asyncio.gather(*tasks)


asyncio.run(main(usernames, accounts, proxies))
