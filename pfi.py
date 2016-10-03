# Sample code from the tutorial 'Pandas from the Inside'
# Stephen Simmons - mail@stevesimmons.com
# PyData London, Fri 6 May 2016
#
# Requires Python3, Pandas, Numpy. Best with IPython and Pandas 0.18.0.
# Note: has a workaround for an indexing bug in pandas 0.18.0.


import numpy as np
import pandas as pd
print("numpy=%s; pandas=%s" % (np.__version__, pd.__version__))

import csv
import os


# Better output formatting defaults
pd.options.display.max_rows = 20
pd.options.display.width = 200

def main():
    if not os.path.exists('bg3.txt'):
        # Download bg3.txt from www.afltables.com
        download_sample_data()

    df = load_scores()
    scores = prepare_scores(df)
    ladder = calc_ladder(scores)
    return scores, ladder


def download_sample_data():
    '''
    Download results of every AFL match from www.afltables.com
    (14800 games since 1897)
    '''
    import urllib.request

    base_url = 'http://afltables.com/afl/stats/biglists/'
    for filename in ('bg3.txt', 'bg7.txt'):
        url = base_url + filename
        print("Downloading from %s" % url)
        txt = urllib.request.urlopen(url).read()
        with open(filename, 'wb') as f:
            f.write(txt)
            print("Wrote %d bytes to %s" % ( len(txt), filename ))


def load_scores(filename='bg3.txt'):
    '''
    Pandas DataFrames from loading csv files bg3.txt (games) or
    bg7.txt (attendance) csvs downloaded from www.afltables.com.
    '''
    if filename == 'bg3.txt':
        # Scores with rounds
        # - GameNum ends with '.', single space for nums > 100k
        # - Rounds are 'R1'-'R22' or 'QF', 'PF', 'GF'.
        # - Three grand finals were drawn and replayed the next week
        # - Scores are strings '12.5.65' with goals/behinds/points
        # - Venue may end with a '.', e.g. 'M.C.G.' though always at EOL
        cols = 'GameNum Date Round HomeTeam HomeScore AwayTeam AwayScore Venue'
        sep = '[. ] +'
        sep = '[. ] +'

    elif filename == 'bg7.txt':
        # Attendance stats
        # - RowNum ends with '.', single space for nums > 100k
        # - Spectators ends with '*' for finals games
        # - Venue may end with a '.', e.g. 'M.C.G.'
        # - Dates are 'dd-Mmm-yyyy'.
        # - Date/Venue unique, except for two days in 1980s, when
        #   M.C.G. hosted games at 2pm and 5pm with same num of spectators.
        cols = 'RowNum Spectators HomeTeam HomeScore AwayTeam AwayScore Venue Date'
        sep = '(?:(?<=[0-9])[.*] +)|(?:  +)'

    else:
        raise ValueError("Unexpected data file")

    df = pd.read_csv(filename, skiprows=2, sep=sep,
                     names=cols.split(), parse_dates=['Date'],
                     quoting=csv.QUOTE_NONE, engine='python')
    return df


def prepare_scores(df):
    '''
    DataFrame with rows giving each team's results in a game
    (1 game -> 2 rows for home and away teams)
    '''
    scores_raw = df.drop('GameNum', axis=1).set_index(['Date', 'Venue', 'Round'])

    # Convert into sections for both teams
    home_teams = scores_raw['HomeTeam'].rename('Team')
    away_teams = scores_raw['AwayTeam'].rename('Team')

    # Split the score strings into Goals/Behinds, and points For and Against
    regex = '(?P<G>\d+).(?P<B>\d+).(?P<F>\d+)'
    home_scores = scores_raw['HomeScore'].str.extract(regex, expand=True).astype(int)
    away_scores = scores_raw['AwayScore'].str.extract(regex, expand=True).astype(int)
    home_scores['A'] = away_scores['F']
    away_scores['A'] = home_scores['F']

    home_games = pd.concat([home_teams, home_scores], axis=1)
    away_games = pd.concat([away_teams, away_scores], axis=1)

    scores = home_games.append(away_games).sort_index().set_index('Team', append=True)
    # scores = pd.concat([home_games, away_games], axis=0).sort_index()

    # Rather than moving Team to MultiIndex with scores.set_index('Team', append=True),
    # keep it as a data column so we can see what an inhomogeneous DataFrame looks like.
    return scores


def calc_ladder(scores_df, year=2016):
    '''
    DataFrame with championship ladder with round-robin games for the given year.
    Wins, draws and losses are worth 4, 2 and 0 points respectively.
    '''
    # Select a subset of the rows
    # df.loc[] matches dates as strings like '20160506' or '2016'.
    # Note here rounds are simple strings so sort with R1 < R10 < R2 < .. < R9
    #      (we could change this with a CategoricalIndex)
    # Note also that pandas 0.18.0 has a bug with .loc on MultiIndexes
    #      if dates are the first level. It works as expected if we
    #      move the dates to the end before slicing
    scores2 = scores_df.reorder_levels([1, 2, 3, 0]).sort_index()
    x = scores2.loc(axis=0)[:, 'R1':'R9', :, str(year):str(year)]
    # Don't need to put levels back in order as we are about to drop 3 of them
    # x = x.reorder_levels([3, 0, 1, 2]).sort_index()

    # Just keep Team. This does a copy too, avoiding SettingWithCopy warning
    y = x.reset_index(['Date', 'Venue', 'Round'], drop=True)

    # Add cols with 0/1 for number of games played, won, drawn and lost
    y['P'] = 1
    y['W'] = (y['F'] > y['A']).astype(int)
    y['D'] = 0
    y.loc[y['F'] == y['A'], 'D'] = 1
    y.eval('L = 1*(A>F)', inplace=True)
    print(y)

    # Subtotal by team and then sort by Points/Percentage
    t = y.groupby(level='Team').sum()
    t['PCT'] = 100.0 * t.F / t.A
    t['PTS'] = 4 * t['W'] + 2 * t['D']
    ladder = t.sort_values(['PTS', 'PCT'], ascending=False)

    # Add ladder position (note: assumes no ties!)
    ladder['Pos'] = pd.RangeIndex(1, len(ladder) + 1)
    print(ladder)

    return ladder



if __name__ == '__main__':
    main()