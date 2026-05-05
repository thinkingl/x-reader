import React, { useState, useEffect, useRef } from 'react';
import { Form, Input, Select, InputNumber, Button, Card, message, Alert, Spin, Switch, Typography, Divider, Tabs, Tag, Space, Tooltip } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, AudioOutlined, LockOutlined, UnlockOutlined, CloudOutlined, DesktopOutlined, SettingOutlined, ExperimentOutlined, QuestionCircleOutlined, HourglassOutlined } from '@ant-design/icons';
import api from '../api';
import { useAuth } from '../AuthContext';

const { Title, Text, Paragraph } = Typography;

// MiMo 内置语音列表 (来自 MiMo V2.5 TTS Skill)
const MIMO_VOICES = [
  { id: 'mimo_default', name: 'MiMo-默认', lang: '自动', gender: '-', style: '自动选择' },
  { id: '冰糖', name: '冰糖', lang: '中文', gender: '女', style: '活泼少女' },
  { id: '茉莉', name: '茉莉', lang: '中文', gender: '女', style: '知性女声' },
  { id: '苏打', name: '苏打', lang: '中文', gender: '男', style: '阳光少年' },
  { id: '白桦', name: '白桦', lang: '中文', gender: '男', style: '成熟男声' },
  { id: 'Mia', name: 'Mia', lang: '英文', gender: '女', style: 'Lively girl' },
  { id: 'Chloe', name: 'Chloe', lang: '英文', gender: '女', style: 'Sweet Dreamy' },
  { id: 'Milo', name: 'Milo', lang: '英文', gender: '男', style: 'Sunny boy' },
  { id: 'Dean', name: 'Dean', lang: '英文', gender: '男', style: 'Steady Gentle' },
];

// MiMo 模型列表
const MIMO_MODELS = [
  { id: 'mimo-v2.5-tts', name: 'MiMo-V2.5-TTS', desc: '预置高品质音色，支持音频标签、风格控制、唱歌' },
  { id: 'mimo-v2.5-tts-voicedesign', name: 'MiMo-V2.5-TTS-VoiceDesign', desc: '文本描述定制音色（性别/年龄/质感/情绪）' },
  { id: 'mimo-v2.5-tts-voiceclone', name: 'MiMo-V2.5-TTS-VoiceClone', desc: '音频样本复刻任意音色' },
];

function Configuration() {
  const [config, setConfig] = useState(null);
  const [presets, setPresets] = useState([]);
  const [activeTab, setActiveTab] = useState('engine');
  const { isAuthEnabled, enableAuth, disableAuth, logout } = useAuth();

  // 测试相关状态
  const [testText, setTestText] = useState('你好，这是一段测试文本。');
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef(null);

  // 测试模式：preset（使用预设）或 custom（自定义参数）
  const [testMode, setTestMode] = useState('preset');
  const [testPreset, setTestPreset] = useState(null);
  // 自定义参数
  const [testEngine, setTestEngine] = useState('local_omnivoice');
  const [testVoiceMode, setTestVoiceMode] = useState('clone');
  const [testVoiceId, setTestVoiceId] = useState('冰糖');
  const [testInstruct, setTestInstruct] = useState('');
  const [testRefAudio, setTestRefAudio] = useState('');
  const [testRefText, setTestRefText] = useState('');
  const [testNumStep, setTestNumStep] = useState(32);
  const [testGuidanceScale, setTestGuidanceScale] = useState(2.0);
  const [testSpeed, setTestSpeed] = useState(1.0);

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

      if (testMode === 'preset' && testPreset) {
        formData.append('voice_preset_id', testPreset);
      } else {
        // 自定义参数
        formData.append('engine', testEngine);
        formData.append('voice_mode', testVoiceMode);
        if (testInstruct) formData.append('instruct', testInstruct);
        if (testRefAudio) formData.append('ref_audio_path', testRefAudio);
        if (testRefText) formData.append('ref_text', testRefText);
        if (testEngine === 'online_mimo') {
          if (testVoiceMode === 'auto') formData.append('voice_id', testVoiceId);
        }
        if (testEngine === 'local_omnivoice') {
          formData.append('num_step', testNumStep);
          formData.append('guidance_scale', testGuidanceScale);
          formData.append('speed', testSpeed);
        }
      }

      const res = await api.post('/api/config/test', formData, {
        timeout: 600000,
      });
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

  // 渲染 TTS 引擎配置
  const renderEngineConfig = () => (
    <Card title={<><SettingOutlined /> TTS 引擎配置</>} style={{ marginBottom: 16 }}>
      <Form layout="vertical" initialValues={config} onFinish={handleConfigSave}>
        <Divider orientation="left">本地模型配置</Divider>
        
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

        <Divider orientation="left">在线 API 配置 (MiMo-V2.5-TTS)</Divider>

        <Form.Item 
          label={
            <Space>
              <span>API Key</span>
              <Tooltip title="在 platform.xiaomimimo.com 获取 API Key">
                <QuestionCircleOutlined />
              </Tooltip>
            </Space>
          } 
          name="mimo_api_key"
        >
          <Input.Password placeholder="输入 MiMo API Key" />
        </Form.Item>

        <Form.Item 
          label={
            <Space>
              <span>API Base URL</span>
              <Tooltip title="MiMo API 的基础 URL 地址">
                <QuestionCircleOutlined />
              </Tooltip>
            </Space>
          } 
          name="mimo_base_url"
        >
          <Input placeholder="https://token-plan-cn.xiaomimimo.com/v1" />
        </Form.Item>

        <Form.Item label="默认模型" name="mimo_model">
          <Select 
            options={MIMO_MODELS.map(m => ({ 
              label: `${m.name} - ${m.desc}`, 
              value: m.id 
            }))} 
          />
        </Form.Item>

        <Form.Item label="默认语音" name="mimo_default_voice">
          <Select 
            showSearch
            optionFilterProp="label"
            options={MIMO_VOICES.map(v => ({ 
              label: `${v.name} - ${v.style} (${v.lang}/${v.gender})`, 
              value: v.id 
            }))} 
          />
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

        <Form.Item label="并发数" name="concurrency">
          <InputNumber min={1} max={8} />
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
  );

  // 渲染文本分段配置
  const renderChunkConfig = () => (
    <Card title={<><DesktopOutlined /> 文本分段配置</>} style={{ marginBottom: 16 }}>
      <Alert
        message="文本分段说明"
        description={
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li>本地模型：较短的分段可以减少内存占用，但会增加处理次数</li>
            <li>在线 API：较长的分段可以减少 API 调用次数，节省费用</li>
            <li>建议：本地模型 200-300 字符，在线 API 500-1000 字符</li>
          </ul>
        }
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />
      
      <Form layout="vertical" initialValues={config} onFinish={handleConfigSave}>
        <Divider orientation="left">
          <Space>
            <DesktopOutlined /> 本地模型分段
          </Space>
        </Divider>
        
        <Form.Item 
          label="本地文本分段大小（字符）" 
          name="local_chunk_size"
          extra="每段文本的最大字符数，影响内存占用和处理速度"
        >
          <InputNumber min={50} max={500} step={10} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item 
          label="本地分段间隔（秒）" 
          name="local_chunk_gap"
          extra="合并音频时，段落之间的静音间隔"
        >
          <InputNumber min={0.1} max={2.0} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        <Divider orientation="left">
          <Space>
            <CloudOutlined /> 在线 API 分段
          </Space>
        </Divider>

        <Form.Item 
          label="在线文本分段大小（字符）" 
          name="online_chunk_size"
          extra="每段最大字符数。V2.5 单次支持 2500 字，建议 1500-2000 字以保稳定"
        >
          <InputNumber min={200} max={2500} step={100} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item 
          label="在线分段间隔（秒）" 
          name="online_chunk_gap"
          extra="合并音频时，段落之间的静音间隔"
        >
          <InputNumber min={0.1} max={2.0} step={0.1} style={{ width: '100%' }} />
        </Form.Item>

        <Divider orientation="left">
          <Space>
            <HourglassOutlined /> 超时设置
          </Space>
        </Divider>

        <Form.Item 
          label="TTS 请求超时（秒）" 
          name="tts_timeout"
          extra="单次 TTS 请求/生成的最大等待时间。GPU 较弱时建议调大（如 300-600）"
        >
          <InputNumber min={30} max={3600} step={30} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit">保存配置</Button>
        </Form.Item>
      </Form>
    </Card>
  );

  // 渲染认证设置
  const renderAuthConfig = () => (
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
  );

  // 渲染测试功能
  const renderTestSection = () => (
    <Card title={<><ExperimentOutlined /> 测试语音合成</>} style={{ marginBottom: 16 }}>
      {/* 模式切换 */}
      <div style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
        <Select
          value={testMode}
          onChange={(v) => setTestMode(v)}
          style={{ width: 160 }}
          options={[
            { label: '使用预设', value: 'preset' },
            { label: '自定义参数', value: 'custom' },
          ]}
        />

        {testMode === 'preset' ? (
          <Select
            placeholder="选择语音预设"
            style={{ width: 250 }}
            value={testPreset}
            onChange={setTestPreset}
            allowClear
            options={presets.map(p => ({ label: `${p.name} (${p.engine === 'online_mimo' ? '在线' : '本地'}-${p.voice_mode})`, value: p.id }))}
          />
        ) : (
          <>
            <Select value={testEngine} onChange={setTestEngine} style={{ width: 150 }}
              options={[
                { label: '本地 OmniVoice', value: 'local_omnivoice' },
                { label: '在线 MiMo', value: 'online_mimo' },
              ]} />
            <Select value={testVoiceMode} onChange={setTestVoiceMode} style={{ width: 100 }}
              options={[
                { label: 'clone', value: 'clone' },
                { label: 'design', value: 'design' },
                { label: 'auto', value: 'auto' },
              ]} />
            {testEngine === 'online_mimo' && testVoiceMode === 'auto' && (
              <Select value={testVoiceId} onChange={setTestVoiceId} style={{ width: 160 }}
                options={MIMO_VOICES.map(v => ({ label: v.name, value: v.id }))} />
            )}
            {testVoiceMode === 'design' && (
              <Input placeholder="instruct" value={testInstruct} onChange={e => setTestInstruct(e.target.value)}
                style={{ width: 250 }} />
            )}
          </>
        )}
      </div>

      {/* 本地模型参数 */}
      {testMode === 'custom' && testEngine === 'local_omnivoice' && (
        <div style={{ marginBottom: 16, display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <Space>
            <Text>步数</Text>
            <InputNumber min={1} max={64} value={testNumStep} onChange={setTestNumStep} style={{ width: 80 }} />
          </Space>
          <Space>
            <Text>引导</Text>
            <InputNumber min={1} max={3} step={0.1} value={testGuidanceScale} onChange={setTestGuidanceScale} style={{ width: 80 }} />
          </Space>
          <Space>
            <Text>语速</Text>
            <InputNumber min={0.5} max={2} step={0.1} value={testSpeed} onChange={setTestSpeed} style={{ width: 80 }} />
          </Space>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <Input.TextArea
          rows={3}
          value={testText}
          onChange={(e) => setTestText(e.target.value)}
          placeholder="输入测试文本..."
        />
      </div>

      <Button
        type="primary"
        icon={<AudioOutlined />}
        onClick={handleTest}
        loading={testLoading}
      >
        生成测试音频
      </Button>

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
                {testResult.engine && <Tag color={testResult.engine === 'online' ? 'blue' : 'green'} style={{ marginLeft: 8 }}>{testResult.engine === 'online' ? '在线' : '本地'}</Tag>}
              </div>
              <audio
                ref={audioRef}
                src={testResult.audio_url}
                onEnded={() => setIsPlaying(false)}
                controls
                style={{ width: '100%' }}
              />
            </div>
          </div>
        </div>
      )}
    </Card>
  );

  const tabItems = [
    {
      key: 'engine',
      label: <span><SettingOutlined /> 引擎配置</span>,
      children: renderEngineConfig(),
    },
    {
      key: 'chunk',
      label: <span><DesktopOutlined /> 分段配置</span>,
      children: renderChunkConfig(),
    },
    {
      key: 'auth',
      label: <span><LockOutlined /> 认证设置</span>,
      children: renderAuthConfig(),
    },
    {
      key: 'test',
      label: <span><ExperimentOutlined /> 测试</span>,
      children: renderTestSection(),
    },
  ];

  return (
    <div>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
    </div>
  );
}

export default Configuration;
