import React, { useState, useEffect, useRef } from 'react';
import { Form, Input, Select, InputNumber, Button, Card, message, Alert, Spin, Switch, Typography, Divider } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, AudioOutlined, LockOutlined, UnlockOutlined } from '@ant-design/icons';
import api from '../api';
import { useAuth } from '../AuthContext';

const { Title, Text } = Typography;

function Configuration() {
  const [config, setConfig] = useState(null);
  const [presets, setPresets] = useState([]);
  const { isAuthEnabled, enableAuth, disableAuth, logout } = useAuth();

  // 测试相关状态
  const [testText, setTestText] = useState('你好，这是一段测试文本。用于验证语音合成的效果。');
  const [testPreset, setTestPreset] = useState(null);
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  // 认证相关状态
  const [authKey, setAuthKey] = useState('');
  const [newAuthKey, setNewAuthKey] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  useEffect(() => {
    fetchConfig();
    fetchPresets();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await api.get('/api/config');
      setConfig(res.data);
    } catch (err) {
      message.error('获取配置失败');
    }
  };

  const fetchPresets = async () => {
    try {
      const res = await api.get('/api/voice-presets');
      setPresets(res.data.items);
    } catch (err) {
      message.error('获取语音预设失败');
    }
  };

  const handleConfigSave = async (values) => {
    try {
      await api.put('/api/config', values);
      message.success('配置已保存');
      fetchConfig();
    } catch (err) {
      message.error('保存配置失败');
    }
  };

  // 认证功能
  const handleEnableAuth = async () => {
    if (!newAuthKey.trim()) {
      message.warning('请输入认证密钥');
      return;
    }
    setAuthLoading(true);
    const result = await enableAuth(newAuthKey);
    setAuthLoading(false);
    if (result.success) {
      message.success('认证已启用');
      setNewAuthKey('');
    } else {
      message.error(result.message || '启用认证失败');
    }
  };

  const handleDisableAuth = async () => {
    if (!authKey.trim()) {
      message.warning('请输入当前认证密钥');
      return;
    }
    setAuthLoading(true);
    const result = await disableAuth(authKey);
    setAuthLoading(false);
    if (result.success) {
      message.success('认证已停用');
      setAuthKey('');
      logout();
    } else {
      message.error(result.message || '停用认证失败');
    }
  };

  // 测试功能
  const handleTest = async () => {
    if (!testText.trim()) {
      message.warning('请输入测试文本');
      return;
    }

    setTestLoading(true);
    setTestResult(null);

    try {
      const formData = new FormData();
      formData.append('text', testText);
      if (testPreset) {
        formData.append('voice_preset_id', testPreset);
      }

      const res = await api.post('/api/config/test', formData);
      setTestResult(res.data);
      message.success(res.data.message);
    } catch (err) {
      setTestResult({
        success: false,
        message: '测试失败: ' + (err.response?.data?.detail || err.message),
      });
      message.error('测试失败');
    }
    setTestLoading(false);
  };

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

  if (!config) return <div>加载中...</div>;

  return (
    <div>
      {/* 认证设置卡片 */}
      <Card title={<><LockOutlined /> 认证设置</>} style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 16 }}>
          <Text strong>当前状态: </Text>
          <Text type={isAuthEnabled ? 'success' : 'secondary'}>
            {isAuthEnabled ? '认证已启用' : '认证未启用'}
          </Text>
        </div>

        {!isAuthEnabled ? (
          <div>
            <Title level={5}>启用认证</Title>
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              启用认证后，所有 API 请求需要携带有效的 Token
            </Text>
            <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
              <Input.Password
                placeholder="设置认证密钥"
                value={newAuthKey}
                onChange={(e) => setNewAuthKey(e.target.value)}
                style={{ width: 300 }}
              />
              <Button
                type="primary"
                icon={<LockOutlined />}
                onClick={handleEnableAuth}
                loading={authLoading}
              >
                启用认证
              </Button>
            </div>
          </div>
        ) : (
          <div>
            <Title level={5}>停用认证</Title>
            <Text type="warning" style={{ display: 'block', marginBottom: 16 }}>
              停用认证需要验证当前密钥
            </Text>
            <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
              <Input.Password
                placeholder="输入当前认证密钥"
                value={authKey}
                onChange={(e) => setAuthKey(e.target.value)}
                style={{ width: 300 }}
              />
              <Button
                danger
                icon={<UnlockOutlined />}
                onClick={handleDisableAuth}
                loading={authLoading}
              >
                停用认证
              </Button>
            </div>
          </div>
        )}
      </Card>

      <Card title="TTS 引擎配置" style={{ marginBottom: 16 }}>
        <Form layout="vertical" initialValues={config} onFinish={handleConfigSave}>
          <Form.Item label="模型路径" name="model_path">
            <Input placeholder="本地路径或 HuggingFace repo id" />
          </Form.Item>
          <Form.Item label="设备" name="device">
            <Select options={[
              { label: '自动', value: 'auto' },
              { label: 'CUDA', value: 'cuda' },
              { label: 'CPU', value: 'cpu' },
            ]} />
          </Form.Item>
          <Form.Item label="推理精度" name="precision">
            <Select options={[
              { label: 'Float16', value: 'float16' },
              { label: 'Float32', value: 'float32' },
            ]} />
          </Form.Item>
          <Form.Item label="ASR 模型路径" name="asr_model_path">
            <Input />
          </Form.Item>
          <Form.Item label="并发数" name="concurrency">
            <InputNumber min={1} max={8} />
          </Form.Item>
          <Form.Item label="音频格式" name="audio_format">
            <Select options={[
              { label: 'WAV (无损)', value: 'wav' },
              { label: 'MP3 (通用)', value: 'mp3' },
              { label: 'AAC (高效)', value: 'aac' },
              { label: 'M4A (Apple)', value: 'm4a' },
              { label: 'OGG (开源)', value: 'ogg' },
              { label: 'FLAC (无损压缩)', value: 'flac' },
              { label: 'OPUS (低比特率)', value: 'opus' },
              { label: 'WMA (Windows)', value: 'wma' },
            ]} />
          </Form.Item>
          <Form.Item label="采样率" name="sample_rate">
            <Select options={[
              { label: '24000 Hz', value: 24000 },
              { label: '16000 Hz', value: 16000 },
            ]} />
          </Form.Item>
          <Form.Item label="分块时长（秒）" name="chunk_duration">
            <InputNumber min={5} max={30} step={1} />
          </Form.Item>
          <Form.Item label="分块阈值（秒）" name="chunk_threshold">
            <InputNumber min={15} max={60} step={1} />
          </Form.Item>
          <Form.Item label="文本分段大小（字符）" name="chunk_size">
            <InputNumber min={50} max={500} step={10} />
          </Form.Item>
          <Form.Item label="电子书存储目录" name="book_dir">
            <Input placeholder="data/books" />
          </Form.Item>
          <Form.Item label="音频输出目录" name="audio_dir">
            <Input placeholder="data/audio" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">保存配置</Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 测试功能卡片 */}
      <Card title="测试语音合成" style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 16 }}>
          <Input.TextArea
            rows={3}
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            placeholder="输入测试文本..."
          />
        </div>
        <div style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center' }}>
          <Select
            placeholder="选择语音预设（随机）"
            style={{ width: 250 }}
            value={testPreset}
            onChange={setTestPreset}
            allowClear
            options={presets.map(p => ({ label: p.name, value: p.id }))}
          />
          <Button
            type="primary"
            icon={<AudioOutlined />}
            onClick={handleTest}
            loading={testLoading}
          >
            生成测试音频
          </Button>
        </div>

        {testLoading && (
          <Alert
            message={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Spin size="small" />
                <span>正在生成音频，请稍候...</span>
              </div>
            }
            type="info"
            showIcon={false}
          />
        )}

        {testResult && (
          <Alert
            message={testResult.message}
            type={testResult.success ? 'success' : 'error'}
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        {testResult?.success && testResult?.audio_url && (
          <div style={{ marginTop: 16, padding: 16, background: '#f5f5f5', borderRadius: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <Button
                type="primary"
                shape="circle"
                icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={togglePlay}
                size="large"
              />
              <div style={{ flex: 1 }}>
                <div style={{ marginBottom: 8 }}>
                  时长: {testResult.duration?.toFixed(1)} 秒
                </div>
                <audio
                  ref={audioRef}
                  src={`${api.defaults.baseURL}${testResult.audio_url}`}
                  onEnded={() => setIsPlaying(false)}
                  controls
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

export default Configuration;
