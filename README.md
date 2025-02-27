# Flask Spotify Radio

This project is a Flask application that creates a custom shuffled song radio based on the currently playing track on Spotify. It also integrates with OpenAI and ReccoBeats to provide enhanced track recommendations.

## Features

- **Spotify Integration**: Uses Spotify API to get the currently playing track and generate a custom radio.
- **OpenAI Integration**: Uses OpenAI to get track recommendations based on the currently playing track.
- **ReccoBeats Integration**: Uses ReccoBeats API to get track recommendations based on the currently playing track.

## Prerequisites

- Python 3.9+
- Docker (optional, for containerized deployment)
- Spotify Developer Account
- OpenAI API Key
- ReccoBeats API Access

## Setting Up Spotify App

1. **Create a Spotify Developer Account**:
   - Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications).
   - Log in with your Spotify account or create a new one.

2. **Create a New App**:
   - Click on "Create an App".
   - Fill in the required details (App name, App description).
   - Click "Create".

3. **Get Your Client ID and Client Secret**:
   - After creating the app, you will be redirected to the app's dashboard.
   - Here, you will find your `Client ID` and `Client Secret`.

4. **Set Redirect URI**:
   - In the app's dashboard, click on "Edit Settings".
   - Under "Redirect URIs", add `http://localhost:5002/callback`.
   - Click "Save".

## Setting Up OpenAI API Key

1. **Create an OpenAI Account**:
   - Go to the [OpenAI website](https://www.openai.com/).
   - Sign up for an account or log in if you already have one.

2. **Generate API Key**:
   - Once logged in, navigate to the API section.
   - Click on "Create API Key".
   - Copy the generated API key.

## Environment Variables

Create a `.env` file in the root directory and add the following environment variables:

```env
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:5002/callback
SPOTIFY_SCOPE=user-read-playback-state,user-modify-playback-state
OPENAI_API_KEY=your_openai_api_key
```

Replace the placeholders with your actual credentials.

## Installation

### Clone the Repository

```bash
git clone https://github.com/jsonpoindexter/flask-spotify-radio.git
cd flask-spotify-radio
```

### Set Up Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

### Locally

```bash
flask run
```

The application will be available at `http://localhost:5002`.

### Using Docker

Build and run the Docker container:

```bash
docker-compose up --build
```

The application will be available at `http://localhost:5002`.

## Endpoints

### `/login`

Redirects to Spotify for user authentication.

### `/callback`

Handles the Spotify authentication callback and retrieves the access token.

### `/trigger` (POST)

Triggers a custom shuffled song radio based on the currently playing track.

### `/trigger-openai` (POST)

Triggers a custom radio using OpenAI recommendations.

### `/trigger-reccobeats` (POST)

Triggers a custom radio using ReccoBeats recommendations.

## Example Usage

### Trigger Custom Radio

```bash
curl -X POST http://localhost:5002/trigger
```

### Trigger OpenAI Radio

```bash
curl -X POST http://localhost:5002/trigger-openai
```

### Trigger ReccoBeats Radio

```bash
curl -X POST http://localhost:5002/trigger-reccobeats
```

## Logging

The application logs important events and errors. Logs can be found in the console output.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -am 'Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Create a new Pull Request.

## License

## Contact

For any questions or issues, please open an issue on GitHub.