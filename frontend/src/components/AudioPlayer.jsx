import React, { useState, useRef, useEffect, createContext } from 'react';
import { Button, Slider, Space, Typography, Select } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, SoundOutlined } from '@ant-design/icons';

export const AudioContext = createContext({ playAudio: () => {}, isPlaying: false });

export function AudioProvider({ children }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioInfo, setAudioInfo] = useState(null);
  const audioRef = useRef(null);

  const playAudio = (info) => {
    setAudioInfo(info);
    if (audioRef.current) {
      audioRef.current.src = info.url;
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  return (
    <AudioContext.Provider value={{ playAudio, isPlaying, audioInfo, setAudioInfo, audioRef, setIsPlaying }}>
      {children}
    </AudioContext.Provider>
  );
}

function AudioPlayer() {
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);
  const { isPlaying, audioInfo, setAudioInfo, audioRef, setIsPlaying } = React.useContext(AudioContext);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
      audioRef.current.playbackRate = playbackRate;
    }
  }, [volume, playbackRate]);

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
  };

  const handleSeek = (value) => {
    if (audioRef.current) {
      audioRef.current.currentTime = value;
      setCurrentTime(value);
    }
  };

  const handleVolumeChange = (value) => {
    setVolume(value);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div
      className="audio-player-container"
      style={{ display: audioInfo ? 'block' : 'none' }}
    >
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
      />
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <Button
          type="text"
          icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
          onClick={togglePlay}
          style={{ fontSize: 24 }}
        />
        <div style={{ flex: 1 }}>
          <Typography.Text strong>
            {audioInfo?.bookTitle && `${audioInfo.bookTitle} - `}
            {audioInfo?.title || '未知章节'}
          </Typography.Text>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>{formatTime(currentTime)}</span>
            <Slider
              value={currentTime}
              max={duration}
              onChange={handleSeek}
              style={{ flex: 1 }}
              tooltip={{ formatter: formatTime }}
            />
            <span>{formatTime(duration)}</span>
          </div>
        </div>
        <Space>
          <SoundOutlined />
          <Slider
            value={volume}
            min={0}
            max={1}
            step={0.1}
            onChange={handleVolumeChange}
            style={{ width: 80 }}
          />
          <Select
            value={playbackRate}
            onChange={setPlaybackRate}
            style={{ width: 70 }}
            options={[
              { label: '0.5x', value: 0.5 },
              { label: '1x', value: 1 },
              { label: '1.5x', value: 1.5 },
              { label: '2x', value: 2 },
            ]}
          />
        </Space>
      </div>
    </div>
  );
}

export default AudioPlayer;
