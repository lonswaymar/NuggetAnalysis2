from nba_api.stats.endpoints import LeagueGameFinder 
from nba_api.stats.endpoints import BoxScoreTraditionalV2
from nba_api.stats.endpoints import BoxScoreTraditionalV3
from nba_api.stats.endpoints import BoxScoreAdvancedV3

import time
import numpy as np
import pandas as pd

def get_games_data(season_str, team_ID, num_played=None):
    """
    Get collection of game IDs for a given season and team.
    
    Keyword arguments:
    season_str -- string to denote NBA season, e.g., 2024-2025
    team_ID -- integer for each NBA team.
                      
    Returns a DataFrame with information for each game for given season
    and team.
    """
    
    # Call LeagueGameFinder endpoint from NBA API
    finder = LeagueGameFinder(
        team_id_nullable=team_ID,
        season_nullable=season_str
    )
    games = finder.get_data_frames()[0] # get DataFrame for team and season
    games = games.sort_values('GAME_DATE')  # sort DataFrame by game date
    
    # Remove pre-season games by Season_ID. 12025 for preseason. 22025 for regular.
    games = games[games["SEASON_ID"].astype(int) > 20000]
    
    # Reindex to start at 1
    games.index = games.index + 1
    
    # If gamesPlayedSoFar is not None, then return all games in year
    if num_played is not None:
        games = games[:num_played]
    return games

def get_boxscores(game_ids, name=None, stats_type="traditional", team_name="Nuggets"):
    """
    Return boxscore per game for a given player based on game IDs
    
    Args:
    game_ids -- list or pandas series of game IDs as gotten by get_games_data
    name -- string, firstname-lastname, of a player on roster. e.g, "cameron-johnson"
    
    Returns:
    Pandas DataFrame of advanced metrics for given player per game played.
    """
    all_boxscores = []
    for i, gid in enumerate(game_ids):
        print(f"Processed gameID: {i+1}", flush=True)
        
        if stats_type == "traditional":
            # Traditional stats
            box = BoxScoreTraditionalV3(game_id=gid)
        elif stats_type == "advanced":
            # Advanced stats
            box = BoxScoreAdvancedV3(game_id=gid)
            
        df = box.get_data_frames()[0]  # This has one row per player in that game

        df['GAME_ID'] = gid
        
        # Filter by team name
        df = df[df["teamName"]==team_name]
        
        # Filter by player
        if name is not None:
            df = df[df["playerSlug"] == name]
            
        # Filter by DNP and DND (by minutes played)
        df = df[df["minutes"] != ""]
        
        
            
        all_boxscores.append(df)
        time.sleep(2)  # be nice to the API
        
    full_df = pd.concat(all_boxscores, ignore_index=True)
    full_df.index = full_df.index + 1
    return full_df

def get_pbp(game_ids):
    return

def tidy_axes(ax):
    '''building a function to make my matplotlib figures look a little nicer''' 
    
    # Remove two spines and set color for remaining
    ax.spines['right'].set_visible(False)  # Remove the right vertical line
    ax.spines['top'].set_visible(False)    # Remove the top horizontal line
    ax.spines['left'].set_color((0, 0, 0, 0.5))  # Set the left spine with 50% transparency (alpha = 0.5)
    ax.spines['bottom'].set_color((0, 0, 0, 0.5))  # Set the bottom spine with 50% transparency
    
    # Removes ticks on axes
    # ax.xaxis.set_ticks_position('none')
    # ax.yaxis.set_ticks_position('none')
    
    # Make color of tick labels 0.75
    ax.tick_params(axis='both', which='minor', labelcolor=(0,0,0,.65), color=(0,0,0,.65), labelsize=18, size=4.5)
    ax.tick_params(axis='both', which='major', labelcolor=(0,0,0,.75), color=(0,0,0,.75), labelsize=18, size=5.5)
    
    
    # If axis plotted arrays have labels, format legend.
    if ax.get_legend_handles_labels()[-1] != []:
        ax.legend(frameon=False, fontsize=15, loc="best")
        
        
def compute_time_axis(clock_series, period_series):
    """
    Convert PlayByPlayV3 ISO8601 clock + period into a time axis in minutes.

    Parameters
    ----------
    clock_series : pd.Series
        ISO 8601 clock strings (e.g., 'PT11M44.00S').
    period_series : pd.Series
        Period numbers (1–4 for regulation, 5+ for OT).

    Returns
    -------
    np.ndarray
        Absolute game time in minutes from 0 to end of game.
    """
    
    minutes_remaining = []
    
    for clock_str in clock_series:
        # Remove prefix "PT"
        s = clock_str.replace("PT", "")
        
        # Minutes part
        if "M" in s:
            mins = int(s.split("M")[0])
            sec_part = s.split("M")[1]
        else:
            mins = 0
            sec_part = s
        
        # Seconds part
        secs = float(sec_part.replace("S", ""))
        
        # Convert to minutes
        minutes_remaining.append(mins + secs / 60.0)
    
    minutes_remaining = np.array(minutes_remaining)
    
    # NBA regulation period length in minutes
    PERIOD_LENGTH = 12
    
    # Compute absolute time:
    #   time = time at start of period + elapsed time within period
    time_axis = (period_series - 1) * PERIOD_LENGTH + (PERIOD_LENGTH - minutes_remaining)
    
    return time_axis