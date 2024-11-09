const musicPWA = (function() {
  // Private state
  let state = {
    audioElement: null,
    playlist: [],
    currentIndex: 0,
    callbacks: {
      onTrackChange: null,
      onPlaybackStateChange: null
    },
    mediaSessionEnabled: true
  };

  // Private functions
  function validateTrack(track) {
    if (!track.name || !track.album || !track.sources) {
      throw new Error('Track must contain name, album, and sources');
    }

    // Ensure track has required nested properties
    if (!track.album.artists || track.album.artists.length === 0) {
      throw new Error('Track must have at least one artist');
    }

    return {
      id: track.sources.ytmusic?.id || crypto.randomUUID(),
      order: track.order || 0,
      name: track.name,
      album: {
        name: track.album.name,
        year: track.album.year,
        artists: track.album.artists,
        sources: track.album.sources
      },
      duration: track.duration,
      thumbnail: track.thumbnail,
      sources: track.sources,
      url: track.album.sources?.ytmusic?.url || track.sources?.ytmusic?.url
    };
  }

  function clearMediaSession() {
    if ('mediaSession' in navigator && state.mediaSessionEnabled) {
      // Clear metadata
      navigator.mediaSession.metadata = null;

      // Remove all action handlers
      const actions = [
        'play',
        'pause',
        'previoustrack',
        'nexttrack',
        'seekbackward',
        'seekforward'
      ];

      actions.forEach(action => {
        try {
          navigator.mediaSession.setActionHandler(action, null);
        } catch (error) {
          console.warn(`Could not clear media session action "${action}"`);
        }
      });
    }
  }

  function initMediaSession() {
    if ('mediaSession' in navigator && state.mediaSessionEnabled) {
      const actionHandlers = [
        ['play', () => publicAPI.play()],
        ['pause', () => publicAPI.pause()],
        ['previoustrack', () => publicAPI.previous()],
        ['nexttrack', () => publicAPI.next()],
        ['seekbackward', (details) => {
          const skipTime = details.seekOffset || 10;
          state.audioElement.currentTime = Math.max(state.audioElement.currentTime - skipTime, 0);
        }],
        ['seekforward', (details) => {
          const skipTime = details.seekOffset || 10;
          state.audioElement.currentTime = Math.min(state.audioElement.currentTime + skipTime,
            state.audioElement.duration);
        }]
      ];

      for (const [action, handler] of actionHandlers) {
        try {
          navigator.mediaSession.setActionHandler(action, handler);
        } catch (error) {
          console.warn(`The media session action "${action}" is not supported`);
        }
      }
    }
  }

  function updateMediaSessionMetadata() {
    if ('mediaSession' in navigator && state.mediaSessionEnabled) {
      const currentTrack = state.playlist[state.currentIndex];
      navigator.mediaSession.metadata = new MediaMetadata({
        title: currentTrack.name,
        artist: currentTrack.album.artists.map(artist => artist.name).join(', '),
        album: currentTrack.album.name,
        artwork: currentTrack.thumbnail ? [
          { src: currentTrack.thumbnail.url, sizes: '512x512', type: 'image/jpeg' }
        ] : []
      });
    }
  }

  function handleTrackChange() {
    const currentTrack = state.playlist[state.currentIndex];
    if (currentTrack.url) {
      state.audioElement.src = `//localhost:5000/api/get/${currentTrack.url}`;
      updateMediaSessionMetadata();

      if (state.callbacks.onTrackChange) {
        state.callbacks.onTrackChange(currentTrack);
      }
    } else {
      console.error('Track URL not available');
      handlePlaybackStateChange('error');
    }
  }

  function handlePlaybackStateChange(playbackState) {
    if (state.callbacks.onPlaybackStateChange) {
      state.callbacks.onPlaybackStateChange(playbackState);
    }

    if ('mediaSession' in navigator && state.mediaSessionEnabled) {
      navigator.mediaSession.playbackState = playbackState;
    }
  }

  const publicAPI = {
    init({ audioElement, playlist, onTrackChange, onPlaybackStateChange }) {
      if (!audioElement || !(audioElement instanceof HTMLAudioElement)) {
        throw new Error('Valid audio element is required');
      }

      if (!Array.isArray(playlist) || playlist.length === 0) {
        throw new Error('Valid playlist array is required');
      }

      // Set initial state
      state.audioElement = audioElement;
      state.playlist = playlist.map(validateTrack);
      state.callbacks.onTrackChange = onTrackChange;
      state.callbacks.onPlaybackStateChange = onPlaybackStateChange;
      state.currentIndex = 0;

      // Initialize audio element event listeners
      audioElement.addEventListener('play', () => handlePlaybackStateChange('playing'));
      audioElement.addEventListener('pause', () => handlePlaybackStateChange('paused'));
      audioElement.addEventListener('ended', () => publicAPI.next());
      audioElement.addEventListener('error', () => handlePlaybackStateChange('error'));

      // Initialize media session
      initMediaSession();
      handleTrackChange();

      // Add unload handler
      window.addEventListener('unload', () => publicAPI.cleanup());

      return publicAPI;
    },

    cleanup() {
      if (state.audioElement) {
        state.audioElement.pause();
        state.audioElement.src = ''; // Clear the audio source
        state.audioElement.load(); // Reset the audio element
      }
      clearMediaSession();
      state = {
        audioElement: null,
        playlist: [],
        currentIndex: 0,
        callbacks: {
          onTrackChange: null,
          onPlaybackStateChange: null
        },
        mediaSessionEnabled: true
      };
    },

    play() {
      state.audioElement.play();
      return publicAPI;
    },

    pause() {
      state.audioElement.pause();
      return publicAPI;
    },

    next() {
      state.currentIndex = (state.currentIndex + 1) % state.playlist.length;
      handleTrackChange();
      return publicAPI;
    },

    previous() {
      state.currentIndex = (state.currentIndex - 1 + state.playlist.length) % state.playlist.length;
      handleTrackChange();
      return publicAPI;
    },

    seek(seconds) {
      if (state.audioElement && !isNaN(seconds)) {
        state.audioElement.currentTime = Math.max(0, Math.min(seconds, state.audioElement.duration));
      }
      return publicAPI;
    },

    getCurrentTrack() {
      return state.playlist[state.currentIndex];
    },

    getPlaybackState() {
      if (!state.audioElement) return 'uninitialized';
      if (state.audioElement.error) return 'error';
      return state.audioElement.paused ? 'paused' : 'playing';
    }
  };

  return publicAPI;
})();

// Export for different environments
if (typeof module !== 'undefined' && module.exports) {
  module.exports = musicPWA;
} else if (typeof define === 'function' && define.amd) {
  define([], function() { return musicPWA; });
} else {
  window.musicPWA = musicPWA;
}
