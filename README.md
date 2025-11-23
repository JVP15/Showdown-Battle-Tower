# The Offline Pokemon Battle Tower

Big thanks to [tchataway](https://github.com/tchataway) for the original Poke-Dojo! I have updated it to support the latest version of Poke Env (0.10.0 as of the time I'm writing this) and also made it *truly* offline by using Showdown's damage calculator library ([damage-calc](https://github.com/Smogon/damage-calc)).

In conjunction with an offline Pokemon Showdown server, battle the teams from Brilliant Diamond and Shining Pearl's Singles format Battle Tower.
- Leverages the excellent [`poke-env`](https://github.com/hsahovic/poke-env) library to challenge a player, behaving like the in-game trainer AI does<sup>†</sup>
- Will challenge in 8 sets (sets numbered 1 to 7 and Master class) of 7 trainers each (with the 21st and 49th battles being against Palmer)
	- What trainers and teams appear in each set was taken from [Bulbagarden](https://bulbagarden.net/)'s [Bulbapedia](https://bulbapedia.bulbagarden.net/wiki/List_of_Battle_Tower_Trainers_(Brilliant_Diamond_and_Shining_Pearl))
	- Pokemon data for each team was scraped from [Serebii](https://www.serebii.net/brilliantdiamondshiningpearl/battletower.shtml)

<sup>†</sup>AI has been coded by hand based on observations of in-game behaviour and online research and is still a work-in-progress. If you see erroneous logic, pull requests are most welcome!
## How to Use
### Environment Setup
#### Install `poke-env`
`poke-dojo` makes heavy use of the `poke-env` library. `poke-env` requires python >= 3.6 and a local [Pokemon Showdown](https://github.com/Zarel/Pokemon-Showdown) server.
```
pip install poke-env
```

### Running the Simulator
1. Once your Showdown server is up and running, connect to it and log in.
2. Ensure you have a 3v3 singles format team ready to go.
3. Note your username (top right corner, if you're unfamiliar with Showdown).
4. Create a new folder, `config`, in `poke-dojo`'s root directory.
5. Inside `config`, create a `challenger.txt` file and inside it add the username noted in step 3, and nothing else. E.g., if your username is `SaltyBoi420`, the file would simply contain
```
SaltyBoi420
```
6. In `poke-dojo`'s root directory, run the simulator.
```PowerShell
python .\battle_tower_simulator.py
```
7. Back in Pokemon Showdown, you should have a challenge waiting for you. Accept it and get down to battling!

## Special Thanks to
- [hsahovic](https://github.com/hsahovic) for the excellent `poke-env` library
- [Nineage](https://www.smogon.com/forums/members/nineage.195129/) and [TheFenderStory](https://www.smogon.com/forums/members/222564/) for their damage calculator API
- [Serebii](https://www.serebii.net/), [Smogon](https://www.smogon.com/), and [Bulbagarden](https://bulbagarden.net/) for their amazing, exhaustive data sets

## AI Usage

I only found time to work on this project by justifying it to my company as a way to test out Google's Antigravity and Gemini 3, so I extensively used both of them to refactor this codebase. So if you see something weird here, it's 100% because of AI.