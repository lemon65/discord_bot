import random
from asyncio import sleep

import emoji
import database as db

bjlist = []
hicards = ['K', 'A', 'J', 'Q', '10']

SLOT_PATTERN = [
    emoji.FOUR_LEAF_CLOVER,
    emoji.FOUR_LEAF_CLOVER,
    emoji.MONEY_BAG,
    emoji.MONEY_BAG,
    emoji.MONEY_BAG,
    emoji.POOP,
    emoji.CHERRIES,
    emoji.CHERRIES,
    emoji.CHERRIES,
    emoji.CHERRIES,
    emoji.CHERRIES,
    emoji.CHERRIES,
    emoji.LEMON,
    emoji.LEMON,
    emoji.LEMON,
    emoji.LEMON,
    emoji.LEMON,
    emoji.GRAPES,
    emoji.GRAPES,
    emoji.GRAPES,
    emoji.GRAPES,
    emoji.GRAPES,
    emoji.WATERMELON,
    emoji.WATERMELON,
    emoji.WATERMELON,
    emoji.WATERMELON,
    emoji.STAR
]
SLOT_PATTERN_LITE = [
    'Four leaf clover',
    'Four leaf clover',
    'Money bag',
    'Money bag',
    'Money bag',
    'Poop',
    'Cherries',
    'Cherries',
    'Cherries',
    'Cherries',
    'Cherries',
    'Cherries',
    'Lemon',
    'Lemon',
    'Lemon',
    'Lemon',
    'Lemon',
    'Grapes',
    'Grapes',
    'Grapes',
    'Grapes',
    'Grapes',
    'Watermelon',
    'Watermelon',
    'Watermelon',
    'Watermelon',
    'Star'
]

prizeMultipliers = {
    (3, 'Grapes'): 10,
    (3, 'Cherries'): 10,
    (3, 'Lemon'): 10,
    (3, 'Watermelon'): 20,
    (3, 'Money bag'): 100,
    (3, 'Four leaf clover'): 200,
    (4, 'Grapes'): 25,
    (4, 'Cherries'): 25,
    (4, 'Lemon'): 25,
    (4, 'Watermelon'): 50,
    (4, 'Money bag'): 500,
    (4, 'Four leaf clover'): 1000,
    (4, 'Poop'): 2000,
    (4, 'Star'): 2000,

}


async def get_balance(user):
    async with db.connect() as c:
        balance = await c.fetchval("SELECT balance FROM casino_account WHERE user_id = $1", user.id)
        return balance if balance is not None else 0


async def add_money(user, amount):
    async with db.connect() as c:
        await c.execute("""
            INSERT INTO casino_account AS a
            (user_id, balance)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
            SET balance = GREATEST(0, a.balance + EXCLUDED.balance)
        """, user.id, amount)


async def save_slots_stats(user, amounttobankaccount, winnings):
    await add_money(user, amounttobankaccount)
    if winnings > 0:
        await update_slots_stats(user, 1, 0, winnings, amounttobankaccount)  # In this case, winnings is the bet
        # and amounttobankaccount the actual winnings
    else:
        await update_jackpot(user, abs(amounttobankaccount) / 5)  # 20% of bet will go to jackpot
        await update_slots_stats(user, 0, 1, abs(amounttobankaccount), 0)


async def save_blackjack_stats(user, amount, surrender=False, win=False, loss=False, tie=False, blackjack=False):
    if amount:
        await add_money(user, amount)
    if win:
        await update_blackjack_stats(user, 1, amount, 0, 0, 0, 0, amount)
    if loss:
        await update_blackjack_stats(user, 0, abs(amount), 1, 0, 0, 0, 0)
    if tie:
        await update_blackjack_stats(user, 0, 0, 0, 1, 0, 0, 0)
    if surrender:
        await update_blackjack_stats(user, 0, abs(amount), 0, 0, 1, 0, 0)
    if blackjack:
        await update_blackjack_stats(user, 1, amount, 0, 0, 0, 1, amount)  # A blackjack also counts as a win


async def update_jackpot(user, amount, win=False):
    async with db.connect() as c:
        if win:
            await c.execute("""
                UPDATE casino_jackpot SET jackpot = 0
                """)
            # todo: await updatejackpothistory(user, amount)
        else:
            await c.execute("""
                UPDATE casino_jackpot SET jackpot = jackpot + $1
                """, amount)


async def update_slots_stats(user, wins, losses, moneyspent, moneywon):
    async with db.connect() as c:
        await c.execute("""
            INSERT INTO casino_stats AS a
            (user_id, wins_slots, losses_slots, moneyspent_slots, moneywon_slots)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id) DO UPDATE SET
            wins_slots = GREATEST(0, a.wins_slots + EXCLUDED.wins_slots),
            losses_slots = GREATEST(0, a.losses_slots + EXCLUDED.losses_slots),
            moneyspent_slots = GREATEST(0, a.moneyspent_slots + EXCLUDED.moneyspent_slots),
            moneywon_slots = GREATEST(0, a.moneywon_slots + EXCLUDED.moneywon_slots)
        """, user.id, wins, losses, moneyspent, moneywon)


async def update_blackjack_stats(user, wins, moneyspent, losses, ties, surrenders, blackjack, moneywon):
    async with db.connect() as c:
        await c.execute("""
            INSERT INTO casino_stats AS a
            (user_id, wins_bj, losses_bj, moneyspent_bj, ties, surrenders, bj_blackjack, moneywon_bj)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id) DO UPDATE SET
            wins_bj = GREATEST(0, a.wins_bj + EXCLUDED.wins_bj),
            losses_bj = GREATEST(0, a.losses_bj + EXCLUDED.losses_bj),
            moneyspent_bj = GREATEST(0, a.moneyspent_bj + EXCLUDED.moneyspent_bj),
            ties = GREATEST(0, a.ties + EXCLUDED.ties),
            surrenders = GREATEST(0, a.surrenders + EXCLUDED.surrenders),
            bj_blackjack = GREATEST(0, a.bj_blackjack + EXCLUDED.bj_blackjack),
            moneywon_bj = GREATEST(0, a.moneywon_bj + EXCLUDED.moneywon_bj)
        """, user.id, wins, losses, moneyspent, ties, surrenders, blackjack, moneywon)


async def makedeck(blackjack=True):
    cards = []
    value = 1
    if blackjack:
        value = 6
    for x in range(0, value):
        for suit in [emoji.SPADES, emoji.HEARTS, emoji.CLUBS, emoji.DIAMONDS]:
            for rank in ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']:
                cards.append((rank, suit))
    random.shuffle(cards)
    return cards


async def get_bet(user):
    async with db.connect() as c:
        bet = await c.fetchval("SELECT bet FROM casino_bet WHERE user_id = $1", user.id)
        return bet if bet is not None else 0


async def set_bet(user, amount):
    async with db.connect() as c:
        await c.execute("""
            INSERT INTO casino_bet AS b
            (user_id, bet)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
            SET bet = GREATEST(0, EXCLUDED.bet)
        """, user.id, amount)


async def get_jackpot():
    async with db.connect() as c:
        return await c.fetchrow("""
            SELECT jackpot from casino_jackpot
            """)


# Function to play the slots
async def cmd_slots(client, message, arg, debug=False):
    winnings = 0
    lite = False
    litequilavent = dict(zip(SLOT_PATTERN, SLOT_PATTERN_LITE))
    if arg == 'lite' or arg == 'l':
        lite = True
    player = message.author
    jackpot = await get_jackpot()
    pattern = SLOT_PATTERN
    if lite:
        pattern = SLOT_PATTERN_LITE
    jackpotamount = jackpot['jackpot']
    wheel_list = []
    doubletimes = 0
    if debug:
        pattern = ['Star', 'Star', 'Star', 'Star']
    stay = False
    bet = await get_bet(player)
    if bet < 1:
        await client.send_message(message.channel, 'You need set a valid bet, Example: !bet 5')
        return

    balance = await get_balance(player)
    if balance == 0:
        await client.send_message(message.channel, 'You need to run the !loan command.')
        return

    if bet > 1000:
        await client.send_message(message.channel,
                                  'Please lower your bet. (The maximum allowed bet for slots is 1000.)')
        return

    if bet > balance:
        await client.send_message(message.channel,
                                  'Your balance of $%s is to low, lower your bet amount of $%s' % (
                                      balance, bet))
        return

    def getwinnings(most_common, bet, inrow):
        winnings = prizeMultipliers.get((inrow, most_common)) * bet
        return winnings

    def most_common(lst):
        most_common = max(lst, key=lst.count)
        amount = lst.count(most_common)
        if (amount < 4) and ('Star' in lst or emoji.STAR in lst):
            while 'Star' in lst:
                lst.remove('Star')
            while emoji.STAR in lst:
                lst.remove(emoji.STAR)
        return max(lst, key=lst.count), lst.count(most_common)

    def checkifthreeidentical(x):
        return len(set(x[1:])) == 1 or len(set(x[:-1])) == 1

    def checkiffouridentical(x):
        if emoji.STAR in x and (x.count(emoji.STAR) < 4) or 'Star' in x and (x.count('Star') < 4):
            return len(set(x)) == 2
        return len(set(x)) == 1 or len(set(x)) == 1

    for x in range(0, 4):
        wheel_pick = random.choice(pattern)
        wheel_list.append(wheel_pick)

    most_common, amount = most_common(wheel_list[:])

    if not lite:
        most_common = litequilavent.get(most_common)

    four = checkiffouridentical(wheel_list)
    if four:
        winnings = getwinnings(most_common, bet, 4)

    if not four:
        three = checkifthreeidentical(wheel_list)
        if three and most_common not in ['Poop', 'Star', emoji.STAR, emoji.POOP]:
            winnings = getwinnings(most_common, bet, 3)

    wheel_payload = '%s Bet: $%s --> | ' % (player.name, bet) + ' - '.join(
        wheel_list) + ' |' + ' Outcome: $%s' % winnings
    await client.send_message(message.channel, wheel_payload)

    if amount == 4 and most_common in ['Star', emoji.STAR]:
        if jackpotamount > 0:
            print(jackpotamount)
            await update_jackpot(player.id, jackpotamount, win=True)
        for spam in range(0, 3):
            await client.send_message(message.channel,
                                      'HE HAS DONE IT! %s has won the jackpot of %s!' % (
                                      player.name, winnings + jackpotamount))
            await sleep(1)

    while winnings > 0 and not stay and not lite:
        doubletimes += 1
        if doubletimes == 5:
            await client.send_message(message.channel,
                                      'You have reached the doubling limit! You won %s' % (winnings))
            break
        await client.send_message(message.channel,
                                  'You won %s! Would you like to double? (Type !double or !take)' % (
                                      winnings))
        winnings, stay = await askifdouble(client, message, winnings)
    if winnings > 0:
        await save_slots_stats(player, winnings, bet)
    else:
        await save_slots_stats(player, -bet, 0)


# FIXME: Exact copy of cmd_coin in run_lemon_bot.py
async def cmd_coin(client, message, _):
    coin = random.choice(["Heads", "Tails"])
    await client.send_message(message.channel, "Just a moment, flipping the coin...")
    await sleep(.5)
    await client.send_message(message.channel, "The coin lands on: %s" % coin)
    return coin


async def askifheadsortails(client, message, winnings):
    while True:
        answer = await client.wait_for_message(timeout=60, author=message.author, check=check)
        if answer and answer.content.lower() == 'heads' or answer.content.lower() == 'tails':
            coin = await cmd_coin(client, message, winnings)
            if coin.lower() == answer.content.lower():
                winnings *= 2
                await client.send_message(message.channel,
                                          "You win! $%s" % winnings)
                return winnings
            else:
                await client.send_message(message.channel,
                                          "You lose!")
                winnings = 0
                return winnings


def check(message):
    return message.author == message.author


async def askifdouble(client, message, winnings):
    stay = True
    player = message.author
    answer = await client.wait_for_message(timeout=15, author=player, check=check)
    if answer and answer.content.lower() == '!double':
        await client.send_message(message.channel,
                                  "Type 'heads' or 'tails'")
        winnings = await askifheadsortails(client, message, winnings)
        if winnings > 0:
            stay = False
            return winnings, stay
    elif answer is None or answer.content.lower() == '!slots' or answer.content.lower() == '!take':
        await client.send_message(message.channel,
                                  "You took the money ($%s)" % winnings)
        return winnings, stay
    return winnings, stay


# Function to set a users bet.
async def cmd_bet(client, message, amount):
    if not amount or not amount.isdigit():
        return await client.send_message(message.channel,
                                         'Amount must be numeric and positive, for example: !bet 10')

    amount = int(amount)
    if amount < 1:
        await client.send_message(message.channel,
                                  'You need to enter a positive integer, minimum being 1. Example: !bet 5')
        return
    await set_bet(message.author, amount)
    await client.send_message(message.channel, '%s, set bet to: %s' % (message.author, amount))


# Function to look at the currently Set bet.
async def cmd_reviewbet(client, message, _):
    bet = await get_bet(message.author)
    await client.send_message(message.channel,
                              '%s is currently betting: %s' % (message.author.name, bet))


# function to loan players money -- ONLY UP TO -- > $50 dollars
async def cmd_loan(client, message, _):
    balance = await get_balance(message.author)
    if balance >= 50:
        await client.send_message(message.channel,
                                  '%s you have $%s, you do not need a loan.' % (message.author.name, balance))
        return

    await add_money(message.author, 50 - balance)
    if balance == 0:
        await client.send_message(message.channel, '%s, added $50' % message.author.name)
    else:
        await client.send_message(message.channel, '%s, added up to $50' % message.author.name)


# Function to look up a users Money!
async def cmd_bank(client, message, _):
    balance = await get_balance(message.author)
    await client.send_message(message.channel, 'User: %s, Balance: $%s' % (message.author.name, balance))
    if balance == 0:
        await client.send_message(message.channel, "Looks like you don't have any money, try the !loan command.")


async def getcardrank(card, hand, score):
    rank = card
    letter = card
    if card in ['K', 'J', 'Q', '10']:
        rank = 10
    if card == 'A':
        if score > 10:
            rank = 1
            letter = 'a'
        else:
            rank = 11
    if 'A' in hand and (score + int(rank)) > 21:
        score -= 10
        for n, i in enumerate(hand):
            if i == 'A':
                hand[n] = 'a'
    score += int(rank)
    return int(rank), score, hand, letter


async def dealcard(cards, hand, nofcards, score):
    for x in range(nofcards):
        card1 = cards.pop()
        rank, score, hand, letter = await getcardrank(card1[0], hand, score)
        suit = card1[1]
        hand += [rank, suit, letter]
    return hand, score


async def dealhand(client, message, score, cards, broke, hand, player=True):
    if score == 0:
        if player:
            hand, score = await dealcard(cards, hand, 2, score)
            await sleep(0.2)
            await domessage(client, message, hand[1], hand[2], hand[4], hand[5], score, broke, firstround=True)
            return score, hand
        else:
            hand, score = await dealcard(cards, hand, 2, score)
            await domessage(client, message, hand[1], hand[2], None, None, score, None, player=False, firstround=True)
            return hand[0], hand
    else:
        if player:
            hand, score = await dealcard(cards, hand, 1, score)
            await sleep(0.2)
            await domessage(client, message, hand[-2], hand[-1], None, None, score, broke)
            return score, hand
        else:
            hand, score = await dealcard(cards, hand, 1, score)
            await sleep(0.2)
            await domessage(client, message, hand[-2], hand[-1], None, None, score, None, player=False)
            return score, hand


async def domessage(client, message, card1suit, card1letter, card2suit, card2letter, score, broke,
                    firstround=False, player=True):
    if firstround:
        if player:
            msg = 'Available options: !hitme, !stay, !surrender, !doubledown'
            if broke:
                msg = 'Available options: !hitme, !stay, !surrender'
            if score == 21:
                msg = 'Blackjack!'
            await client.send_message(message.channel,
                                      "DEALER: %s: Your cards: \n"
                                      "%s                     %s\n"
                                      "    %s     and    %s\n"
                                      "        %s                     %s        (%s total)\n"
                                      "%s" % (
                                          message.author.name, card1letter.upper(), card2letter.upper(), card1suit,
                                          card2suit, card1letter.upper(),
                                          card2letter.upper(), score, msg))
        else:
            await client.send_message(message.channel,
                                      "DEALER: Dealer's card is:\n"
                                      " %s\n"
                                      "    %s\n"
                                      "        %s" % (
                                          card1letter.upper(), card1suit, card1letter))
    else:
        if player:
            msg = 'Available options: !hitme, !stay'
            await client.send_message(message.channel,
                                      "DEALER: Your card is: \n"
                                      "%s\n"
                                      "    %s\n"
                                      "         %s       total: %s\n"
                                      "%s" % (
                                          card1letter.upper(), card1suit, card1letter.upper(), score, msg))
        else:
            await client.send_message(message.channel,
                                      "DEALER: Dealer's card is: \n"
                                      "%s\n"
                                      "    %s\n"
                                      "         %s\n"
                                      "                total: %s" % (
                                          card1letter.upper(), card1suit, card1letter.upper(), score))


async def getresponse(client, message, score, cards, broke, hand):
    answer = await client.wait_for_message(timeout=25, author=message.author, check=check)
    if answer and answer.content.lower() == '!hitme':
        score, hand = await dealhand(client, message, score, cards, broke, hand)
        stay = False
        return score, stay, hand
    if answer and answer.content.lower() == '!doubledown':
        if broke:
            await client.send_message(message.channel,
                                      "You don't have enough money for doubledown.")
            stay = False
            return score, stay, hand
        if len(hand) > 6:
            await client.send_message(message.channel,
                                      "Doubledown is only available on the first round.")
            stay = False
            return score, stay, hand
        stay = 'doubledown'
        broke = True
        score, hand = await dealhand(client, message, score, cards, broke, hand)
        return score, stay, hand
    if answer and answer.content.lower() == '!surrender':
        if len(hand) > 6:
            await client.send_message(message.channel,
                                      "Surrender is only available on the first round.")
            stay = False
            return score, stay, hand
        stay = 'surrender'
        return score, stay, hand
    elif answer is None or answer.content.lower() == '!stay':
        stay = True
        return score, stay, hand
    stay = False
    return score, stay, hand


async def cmd_blackjack(client, message, _):
    broke = False
    blackjack = False
    phand = []
    dhand = []
    if message.author in bjlist:
        await client.send_message(message.channel,
                                  'Cannot play: You have an unfinished game.')
        return
    cards = await makedeck(blackjack=True)
    bet = await get_bet(message.author)
    if bet < 1:
        await client.send_message(message.channel, 'You need set a valid bet, Example: !bet 5')
        return

    balance = await get_balance(message.author)
    if balance == 0:
        await client.send_message(message.channel, 'You need to run the !loan command.')
        return
    if bet > balance:
        await client.send_message(message.channel,
                                  'Your balance of $%s is to low, lower your bet amount of $%s' % (
                                      balance, bet))
        return
    if bet * 2 > balance:
        broke = True
    stay = False
    bjlist.append(message.author)
    pscore = 0
    dscore = 0
    # Deal the first hand for the dealer, and then to the player
    dscore, dhand = await dealhand(client, message, dscore, cards, broke, dhand, player=False)
    pscore, phand = await dealhand(client, message, pscore, cards, broke, phand)

    # Player gets a blackjack
    if pscore == 21:
        blackjack = True
        bet *= 1.5
        if dhand[2] not in hicards:
            await dofinalspam(client, message, pscore, dscore, int(bet),
                              blackjack=True)  # If the dealer does not have a blackjack, they lose
            return
        else:
            dscore += dhand[-3]
            await domessage(client, message, dhand[-2], dhand[-1], None, None, dscore, broke, player=False)

    # Player does not have  a blackjack
    while not blackjack:
        if stay is True or pscore == 21:  # Player decided to !stay, or got 21.
            break
        if pscore > 21:  # Player is bust
            await dofinalspam(client, message, pscore, dscore, bet)
            return
        pscore, stay, phand = await getresponse(client, message, pscore, cards, broke,
                                                phand)  # This returns stay, which can be 'surrender', 'doubledown', 'true'.

        # Player decides to do a doubledown, doubling his bet.
        if stay == 'doubledown':
            bet += bet
            if pscore > 21:
                await dofinalspam(client, message, pscore, dscore, bet)
                return
            break

        # Player decides to surrender, giving him half of his bet back.
        if stay == 'surrender':
            bet /= 2
            await dofinalspam(client, message, pscore, dscore, int(bet), surrender=True)
            return
    if dscore > pscore:  # Meaning the dealer already has a higher hand than the player, even though they just have one card
        await dofinalspam(client, message, pscore, dscore, bet)
        return

    if not blackjack and len(
            dhand) == 6 and pscore < 21:  # 'lenght of dhand is 6' means that dealer has two cards in hand.
        dscore += dhand[
            -3]  # Sum the second card into existing score. 'dhand' contains suit, rank and letter of the card.
        await domessage(client, message, dhand[-2], dhand[-1], None, None, dscore, broke, player=False)
    while 17 > dscore and not (blackjack or ('A' in dhand and dscore == 17)):  # Deal dealer's cards
        await sleep(0.2)
        dscore, dhand = await dealhand(client, message, dscore, cards, broke, dhand, player=False)
        if (dscore == pscore and dscore > 16) or (dscore > pscore and dscore > 16) or (dscore > 21) or (
            dscore > pscore):  # Dealer is bust or has a higher score than the player
            break
    # Tell the results of the game with the arguments that were generated from the mess above
    await dofinalspam(client, message, pscore, dscore, bet)


async def dofinalspam(client, message, pscore, dscore, bet, blackjack=False, surrender=False):
    bjlist.remove(message.author)
    if surrender:
        await client.send_message(message.channel,
                                  'DEALER: %s: Player surrenders and receives half of his bet back. ($%s)' % (
                                      message.author.name, bet))
        winnings = -bet
        await save_blackjack_stats(message.author, winnings, surrender=True)
        return

    if pscore > 21:
        await sleep(0.2)
        winnings = -bet
        await save_blackjack_stats(message.author, winnings, loss=True)
        await client.send_message(message.channel,
                                  'DEALER: %s: Player is BUST! House wins! (Total score: %s) \n You lose $%s' % (
                                      message.author.name, pscore, bet))
        return

    if blackjack:
        await sleep(0.2)
        await client.send_message(message.channel, 'DEALER: %s: Player wins with a blackjack! \n You win $%s' %
                                  (message.author.name, int(bet)))
        winnings = int(bet)
        await save_blackjack_stats(message.author, winnings, blackjack=True)
        return

    if dscore > 21:
        await sleep(0.2)
        winnings = bet
        await save_blackjack_stats(message.author, winnings, win=True)
        await client.send_message(message.channel,
                                  'DEALER: %s: Dealer is bust! Player wins! Player score %s, dealer score %s \n You win $%s' % (
                                      message.author.name, pscore, dscore, bet))
        return
    if dscore > pscore:
        await sleep(0.2)
        winnings = -bet
        await save_blackjack_stats(message.author, winnings, loss=True)
        await client.send_message(message.channel,
                                  'DEALER: %s: House wins! Player score %s, dealer score %s \n You lose $%s' % (
                                      message.author.name, pscore, dscore, bet))
        return
    if pscore > dscore:
        await sleep(0.2)
        winnings = bet
        await save_blackjack_stats(message.author, winnings, win=True)
        await client.send_message(message.channel,
                                  'DEALER: %s: Player wins! Player score %s, dealer score %s \n You win $%s' % (
                                      message.author.name, pscore, dscore, bet))
    if pscore == dscore:
        await sleep(0.2)
        await client.send_message(message.channel,
                                  'DEALER: %s: It is a push! Player: %s, house %s. Your bet of %s is returned.' % (
                                      message.author.name, pscore, dscore, bet))
        await save_blackjack_stats(message.author, None, tie=True)
        return


# Function to lookup the money and create a top 5 users.
async def cmd_leader(client, message, _):
    async with db.connect() as c:
        leaders = await c.fetch("""
            SELECT
                row_number() OVER (ORDER BY balance DESC) AS rank,
                name,
                balance
            FROM casino_account
            JOIN discord_user USING (user_id)
            ORDER BY balance
            DESC LIMIT 5
        """)

    if len(leaders) > 0:
        def format_leader(row):
            return '#%s - %s - $%s' % (row[0], row[1], row[2])

        msg = '  |  '.join(map(format_leader, leaders))
        await client.send_message(message.channel, msg)


def register(client):
    return {
        'bet': cmd_bet,
        'reviewbet': cmd_reviewbet,
        'loan': cmd_loan,
        'bank': cmd_bank,
        'leader': cmd_leader,
        'blackjack': cmd_blackjack,
        'slots': cmd_slots,
    }
