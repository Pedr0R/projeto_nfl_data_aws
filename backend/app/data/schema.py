"""Schemas esperados dos CSVs e constantes do campo.

Usado para validar que os arquivos de entrada têm as colunas esperadas antes de
ingerir, com erro claro caso o dataset mude de forma.
"""

# Dimensões do campo (jardas). Ver Figura 1 do README do dataset.
FIELD_LENGTH = 120.0
FIELD_WIDTH = 53.3

# Colunas esperadas em cada CSV pequeno (validação de schema).
GAMES_COLUMNS = [
    "gameId",
    "season",
    "week",
    "gameDate",
    "gameTimeEastern",
    "homeTeamAbbr",
    "visitorTeamAbbr",
]

PLAYS_COLUMNS = [
    "gameId",
    "playId",
    "playDescription",
    "quarter",
    "down",
    "yardsToGo",
    "possessionTeam",
    "defensiveTeam",
    "yardlineSide",
    "yardlineNumber",
    "gameClock",
    "preSnapHomeScore",
    "preSnapVisitorScore",
    "passResult",
    "penaltyYards",
    "prePenaltyPlayResult",
    "playResult",
    "foulName1",
    "foulNFLId1",
    "foulName2",
    "foulNFLId2",
    "foulName3",
    "foulNFLId3",
    "absoluteYardlineNumber",
    "offenseFormation",
    "personnelO",
    "defendersInBox",
    "personnelD",
    "dropBackType",
    "pff_playAction",
    "pff_passCoverage",
    "pff_passCoverageType",
]

PLAYERS_COLUMNS = [
    "nflId",
    "height",
    "weight",
    "birthDate",
    "collegeName",
    "officialPosition",
    "displayName",
]

PFF_COLUMNS = [
    "gameId",
    "playId",
    "nflId",
    "pff_role",
    "pff_positionLinedUp",
    "pff_hit",
    "pff_hurry",
    "pff_sack",
    "pff_beatenByDefender",
    "pff_hitAllowed",
    "pff_hurryAllowed",
    "pff_sackAllowed",
    "pff_nflIdBlockedPlayer",
    "pff_blockType",
    "pff_backFieldBlock",
]

TRACKING_COLUMNS = [
    "gameId",
    "playId",
    "nflId",
    "frameId",
    "time",
    "jerseyNumber",
    "team",
    "playDirection",
    "x",
    "y",
    "s",
    "a",
    "dis",
    "o",
    "dir",
    "event",
]

# Papéis PFF (pff_role).
ROLE_PASS_RUSH = "Pass Rush"
ROLE_PASS_BLOCK = "Pass Block"
ROLE_COVERAGE = "Coverage"
ROLE_PASS = "Pass"
ROLE_PASS_ROUTE = "Pass Route"
