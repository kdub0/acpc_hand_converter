import argparse, collections, itertools, rank, re, sys

HandHistory = collections.namedtuple(
        'HandHistory',
        ['index', 'betting', 'hands', 'board', 'outcome', 'players']
)

def parse_HandHistory(line):
    if len(line) == 0 or line[0] == '#':
        return None

    fields = line.strip().split(':')
    if len(fields) == 0:
        raise RuntimeException('Incorrect number of fields')

    if fields[0] == 'SCORE':
        return None
    elif fields[0] != 'STATE':
        raise RuntimeException('STATE field invalid')

    if len(fields) != 6:
        raise RuntimeException('Incorrect number of fields')

    index = int(fields[1])
    betting = fields[2].split('/')
    if fields[3].find('/') >= 0:
        hands, board = fields[3].split('/', 1)
        hands = hands.split('|')
        board = board.split('/')
    else:
        hands = fields[3].split('|')
        board = []
    outcome = map(float, fields[4].split('|'))
    players = fields[5].split('|')

    def cards(s):
        return [s[i:i+2] for i in range(0, len(s), 2)]
    hands = [cards(x) for x in hands]
    board = [cards(x) for x in board]

    return HandHistory(index, betting, hands, board, outcome, players)

def main():
    parser = argparse.ArgumentParser(description='convert ACPC hand histories to PokerStars format')
    parser.add_argument(
            '--big_blind', type=int, default=100,
            help='Big blind'
    )
    parser.add_argument(
            '--hero', type=str, default=None,
            help='Name of Hero'
    )
    parser.add_argument(
            '--player_map', type=str, default=[], nargs='+',
            help='Map player names (e.g., hyperborian_2pn_2014=Hyperborean)'
    )
    parser.add_argument(
            '--small_blind', type=int, default=50,
            help='Small blind'
    )
    parser.add_argument(
            '--stack_size', type=int, default=20000,
            help='Stack size'
    )
    parser.add_argument(
            '--table_name', type=str, default='ACPC Match',
            help='PokerStars table name'
    )
    parser.add_argument(
            '--start_index', type=int, default=1,
            help='Index of first hand'
    )
    args = parser.parse_args()

    player_map = dict([x.split('=') for x in args.player_map])
    args.hero = player_map.get(args.hero, args.hero)

    index = args.start_index
    for line in sys.stdin.xreadlines():
        hand = parse_HandHistory(line)
        if hand:
            hand_players = [player_map.get(x, x) for x in hand.players]
            if index == args.start_index:
                players = hand_players

            if players[0] == hand_players[0] and players[1] == hand_players[1]:
                dealer = 1
            elif players[0] == hand_players[1] and players[1] == hand_players[0]:
                dealer = 0
            else:
                players = hand_players
                dealer = 1

            if hand_players[0] == args.hero:
                hero = 0
            elif hand_players[1] == args.hero:
                hero = 1
            else:
                hero = None

            if index > args.start_index:
                print

            # add in time
            print 'PokerStars Hand #%d: Hold\'em No Limit ($%d/$%d USD)' % (
                    index, args.small_blind, args.big_blind
            )

            print 'Table \'%s\' heads-up Seat #%d is the button' % (
                    args.table_name,
                    1 + dealer
            )

            print 'Seat 1: %s ($%d in chips)' % (players[0], args.stack_size)
            print 'Seat 2: %s ($%d in chips)' % (players[1], args.stack_size)

            print '%s: posts small blind $%d' % (hand_players[1], args.small_blind)
            print '%s: posts big blind $%d' % (hand_players[0], args.big_blind)

            print '*** HOLE CARDS ***'
            if hero is not None:
                print 'Dealt to %s [%s %s]' % (
                        hand_players[hero],
                        hand.hands[hero][0], hand.hands[hero][1],
                )

            def summary(name1, outcome1, name2, outcome2, pot):
                if name2 == players[0]:
                    name1, name2 = name2, name1
                    outcome1, outcome2 = outcome2, outcome1
                print '*** SUMMARY ***'
                print 'Total pot $%d | Rake $0' % pot

                if len(hand.board) > 0:
                    print 'Board [%s]' % ' '.join(list(itertools.chain(*hand.board)))
                print 'Seat 1: %s %s %s' % (
                        players[0],
                        '(button) (small blind)' if dealer == 0 else '(big blind)',
                        outcome1
                )
                print 'Seat 2: %s %s %s' % (
                        players[1],
                        '(button) (small blind)' if dealer == 1 else '(big blind)',
                        outcome2
                )

            pot = [args.big_blind, args.small_blind]
            for rnd in range(1+len(hand.board)):
                if rnd > 0:
                    print '*** %s **** [%s]' % (
                            ['FLOP', 'TURN', 'RIVER'][rnd - 1],
                            ' '.join(hand.board[rnd-1])
                    )

                player = 1 if rnd == 0 else 0
                betting = hand.betting[rnd] if rnd < len(hand.betting) else ''
                first_action = True

                while betting != '':
                    opponent = 1 - player

                    if betting[0] == 'f':
                        betting = betting[1:]
                        print '%s: folds' % (hand_players[player])
                        if pot[player] < pot[opponent] and pot[opponent] > args.big_blind:
                            print 'Uncalled bet ($%d) returned to %s' % (
                                    pot[opponent] - pot[player],
                                    hand_players[opponent]
                            )
                            outcome = 2*pot[player]
                        else:
                            outcome = pot[player] + pot[opponent]
                        print '%s collected $%d from the pot' % (
                                hand_players[opponent],
                                outcome
                        )

                        folder = 'folded %s' % ['before the Flop',
                                'on the Flop',
                                'on the Turn',
                                'on the River'][rnd]
                        winner = 'collected ($%d)' % outcome
                        summary(hand_players[player], folder,
                                hand_players[opponent], winner,
                                outcome)

                    elif betting[0] == 'c':
                        betting = betting[1:]
                        if pot[player] == pot[opponent]:
                            print '%s: checks' % (hand_players[player])
                        else:
                            print '%s: calls $%d%s' % (
                                    hand_players[player],
                                    pot[opponent] - pot[player],
                                    ' and is all-in' if pot[opponent] == args.stack_size else ''
                            )
                        pot[player] = pot[opponent]

                        if rnd == 3 and not first_action:
                            print '*** SHOW DOWN ***'

                            board_cards = list(itertools.chain(*hand.board))
                            opponent_rank, opponent_rank_name = rank.high(
                                    rank.string_to_cards(
                                        ''.join(hand.hands[opponent]+board_cards)
                                    )
                            )
                            print '%s: shows [%s %s] (%s)' % (
                                    hand_players[opponent],
                                    hand.hands[opponent][0], hand.hands[opponent][1],
                                    opponent_rank_name
                            )

                            player_rank, player_rank_name = rank.high(
                                    rank.string_to_cards(
                                        ''.join(hand.hands[player]+board_cards)
                                    )
                            )
                            print '%s: shows [%s %s] (%s)' % (
                                    hand_players[player],
                                    hand.hands[player][0], hand.hands[player][1],
                                    player_rank_name
                            )

                            win_amount = pot[player] + pot[opponent]
                            outcome = win_amount
                            if opponent_rank == player_rank:
                                win_amount = win_amount / 2

                            if opponent_rank >= player_rank:
                                print '%s collected $%d from pot' % (
                                        hand_players[opponent],
                                        win_amount
                                )
                            if player_rank >= opponent_rank:
                                print '%s collected $%d from pot' % (
                                        hand_players[player],
                                        win_amount
                                )

                            player_outcome = 'showed [%s %s] and %s with %s' % (
                                    hand.hands[player][0], hand.hands[player][1],
                                    'won ($%d)' % win_amount if player_rank >= opponent_rank else 'lost',
                                    player_rank_name
                            )
                            opponent_outcome = 'showed [%s %s] and %s with %s' % (
                                    hand.hands[opponent][0], hand.hands[opponent][1],
                                    'won ($%d)' % win_amount if opponent_rank >= player_rank else 'lost',
                                    opponent_rank_name
                            )
                            summary(hand_players[player], player_outcome,
                                    hand_players[opponent], opponent_outcome,
                                    outcome)

                    elif betting[0] == 'r':
                        betting = betting[1:]
                        size = re.match(r'\d+', betting).group(0)
                        betting = betting[len(size):]
                        size = int(size)

                        print '%s: raises $%d to $%d%s' % (
                                hand_players[player],
                                size - pot[opponent], size,
                                ' and is all-in' if size == args.stack_size else ''
                        )
                        pot[player] = size
                    else:
                        assert False

                    player = (1 + player) % 2
                    first_action = False

            index += 1

if __name__ == '__main__':
    main()
