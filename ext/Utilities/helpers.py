import discord

def get_discord_name(member: discord.Member) -> str:
    discord_name = member.name
    # add "#1234" if it exists
    discriminator = str(member.discriminator)
    if discriminator != "0":
        discord_name += "#" + discriminator
    return discord_name

class PlayerScore:
    def __init__(self, member: discord.Member,
                       raw_score: int,
                       num_chombo: int=0):
        # the default values correspond to an AI opponent (not a real player)
        self.discord_name = get_discord_name(member)
        self.mention = member.mention
        self.raw_score = raw_score
        self.num_chombo = num_chombo

    # comparisons are for the scores only (i.e., not discord names)
    def __eq__(self, other: object) -> bool:
        if isinstance(other, PlayerScore):
            return self.raw_score == other.raw_score
        return NotImplemented
    
    def __lt__(self, other: object) -> bool:
        if isinstance(other, PlayerScore):
            return self.raw_score < other.raw_score
        return NotImplemented

    def __str__(self) -> str:
        """
        used for rendering the player score in output
        """
        if self.num_chombo > 0:
            return f"{self.mention}: {self.raw_score} with {self.num_chombo} chombo"
        else:
            return f"{self.mention}: {self.raw_score}"

    def __repr__(self) -> str:
        return self.__str__()