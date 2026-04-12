import React, { useState, useEffect, useRef } from 'react';
import { Form, Input, Select, InputNumber, Button, Switch, Card, message, Table, Modal, Space, Divider, Upload, Alert } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, StarOutlined, StarFilled, AudioOutlined, UploadOutlined, PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import api from '../api';

// Voice design options from OmniVoice
const genderOptions = [
  { label: '不限', value: '' },
  { label: '男 (male)', value: 'male' },
  { label: '女 (female)', value: 'female' },
];

const ageOptions = [
  { label: '不限', value: '' },
  { label: '儿童 (child)', value: 'child' },
  { label: '少年 (teenager)', value: 'teenager' },
  { label: '青年 (young adult)', value: 'young adult' },
  { label: '中年 (middle-aged)', value: 'middle-aged' },
  { label: '老年 (elderly)', value: 'elderly' },
];

const pitchOptions = [
  { label: '不限', value: '' },
  { label: '极低音调 (very low pitch)', value: 'very low pitch' },
  { label: '低音调 (low pitch)', value: 'low pitch' },
  { label: '中音调 (moderate pitch)', value: 'moderate pitch' },
  { label: '高音调 (high pitch)', value: 'high pitch' },
  { label: '极高音调 (very high pitch)', value: 'very high pitch' },
];

const styleOptions = [
  { label: '不限', value: '' },
  { label: '耳语 (whisper)', value: 'whisper' },
];

const accentOptions = [
  { label: '不限', value: '' },
  { label: '美式口音 (american accent)', value: 'american accent' },
  { label: '英式口音 (british accent)', value: 'british accent' },
  { label: '澳式口音 (australian accent)', value: 'australian accent' },
  { label: '加拿大口音 (canadian accent)', value: 'canadian accent' },
  { label: '印度口音 (indian accent)', value: 'indian accent' },
  { label: '中国口音 (chinese accent)', value: 'chinese accent' },
  { label: '韩国口音 (korean accent)', value: 'korean accent' },
  { label: '日本口音 (japanese accent)', value: 'japanese accent' },
  { label: '葡萄牙口音 (portuguese accent)', value: 'portuguese accent' },
  { label: '俄罗斯口音 (russian accent)', value: 'russian accent' },
];

const dialectOptions = [
  { label: '不限', value: '' },
  { label: '河南话', value: '河南话' },
  { label: '陕西话', value: '陕西话' },
  { label: '四川话', value: '四川话' },
  { label: '贵州话', value: '贵州话' },
  { label: '云南话', value: '云南话' },
  { label: '桂林话', value: '桂林话' },
  { label: '济南话', value: '济南话' },
  { label: '石家庄话', value: '石家庄话' },
  { label: '甘肃话', value: '甘肃话' },
  { label: '宁夏话', value: '宁夏话' },
  { label: '青岛话', value: '青岛话' },
  { label: '东北话', value: '东北话' },
];

const languageOptions = [
  { label: '自动检测', value: '' },
  { label: '中文 (zh)', value: 'zh' },
  { label: 'English (en)', value: 'en' },
  { label: '日本語 (ja)', value: 'ja' },
  { label: '한국어 (ko)', value: 'ko' },
  { label: 'Français (fr)', value: 'fr' },
  { label: 'Deutsch (de)', value: 'de' },
  { label: 'Español (es)', value: 'es' },
  { label: 'Italiano (it)', value: 'it' },
  { label: 'Português (pt)', value: 'pt' },
  { label: 'Русский (ru)', value: 'ru' },
  { label: 'العربية (ar)', value: 'ar' },
  { label: 'हिन्दी (hi)', value: 'hi' },
  { label: 'ไทย (th)', value: 'th' },
  { label: 'Tiếng Việt (vi)', value: 'vi' },
  { label: 'Indonesia (id)', value: 'id' },
  { label: 'Türkçe (tr)', value: 'tr' },
  { label: 'Polski (pl)', value: 'pl' },
  { label: 'Nederlands (nl)', value: 'nl' },
  { label: 'Svenska (sv)', value: 'sv' },
];

function VoicePresets() {
  const [presets, setPresets] = useState([]);
  const [presetModalVisible, setPresetModalVisible] = useState(false);
  const [editingPreset, setEditingPreset] = useState(null);
  const [presetForm] = Form.useForm();
  const voiceMode = Form.useWatch('voice_mode', presetForm);

  // 上传相关状态
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [uploadedAudioPath, setUploadedAudioPath] = useState(null);  // 文件系统路径
  const [uploadedAudioUrl, setUploadedAudioUrl] = useState(null);    // API播放路径
  const [transcribedText, setTranscribedText] = useState('');
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    fetchPresets();
  }, []);

  const fetchPresets = async () => {
    try {
      const res = await api.get('/api/voice-presets');
      setPresets(res.data.items);
    } catch (err) {
      message.error('获取语音预设失败');
    }
  };

  const buildInstruct = (values) => {
    const parts = [];
    if (values.gender) parts.push(values.gender);
    if (values.age) parts.push(values.age);
    if (values.pitch) parts.push(values.pitch);
    if (values.style) parts.push(values.style);
    if (values.accent) parts.push(values.accent);
    if (values.dialect) parts.push(values.dialect);
    return parts.join(', ');
  };

  const parseInstruct = (instruct) => {
    if (!instruct) return {};
    const parts = instruct.split(/[,，]/).map(s => s.trim());
    const result = {};
    for (const part of parts) {
      if (['male', 'female'].includes(part)) result.gender = part;
      else if (['child', 'teenager', 'young adult', 'middle-aged', 'elderly'].includes(part)) result.age = part;
      else if (part.includes('pitch')) result.pitch = part;
      else if (part === 'whisper') result.style = part;
      else if (part.includes('accent')) result.accent = part;
      else if (['河南话', '陕西话', '四川话', '贵州话', '云南话', '桂林话', '济南话', '石家庄话', '甘肃话', '宁夏话', '青岛话', '东北话'].includes(part)) result.dialect = part;
    }
    return result;
  };

  const handlePresetSave = async (values) => {
    try {
      const instruct = buildInstruct(values);
      const data = {
        name: values.name,
        voice_mode: values.voice_mode,
        instruct: instruct || null,
        ref_audio_path: uploadedAudioPath || values.ref_audio_path,  // 使用文件系统路径
        ref_text: transcribedText || values.ref_text,
        language: values.language || null,
        num_step: values.num_step,
        guidance_scale: values.guidance_scale,
        speed: values.speed,
        is_default: values.is_default,
      };

      if (editingPreset) {
        await api.put(`/api/voice-presets/${editingPreset.id}`, data);
      } else {
        await api.post('/api/voice-presets', data);
      }
      message.success(editingPreset ? '预设已更新' : '预设已创建');
      setPresetModalVisible(false);
      setEditingPreset(null);
      presetForm.resetFields();
      setUploadedAudioPath(null);
      setUploadedAudioUrl(null);
      setTranscribedText('');
      fetchPresets();
    } catch (err) {
      message.error('保存预设失败');
    }
  };

  const handlePresetDelete = async (id) => {
    try {
      await api.delete(`/api/voice-presets/${id}`);
      message.success('预设已删除');
      fetchPresets();
    } catch (err) {
      message.error('删除预设失败');
    }
  };

  const handleSetDefault = async (id) => {
    try {
      await api.patch(`/api/voice-presets/${id}/set-default`);
      message.success('已设为默认');
      fetchPresets();
    } catch (err) {
      message.error('设置默认失败');
    }
  };

  const handleEditPreset = (preset) => {
    setEditingPreset(preset);
    const parsed = parseInstruct(preset.instruct);
    presetForm.setFieldsValue({
      ...preset,
      ...parsed,
    });
    // 将文件系统路径转换为 API 播放路径
    if (preset.ref_audio_path) {
      setUploadedAudioPath(preset.ref_audio_path);
      // 从路径中提取文件名，构建 API URL
      const filename = preset.ref_audio_path.split('/').pop();
      setUploadedAudioUrl(`/api/reference-audio/${filename}`);
    }
    setTranscribedText(preset.ref_text || '');
    setPresetModalVisible(true);
  };

  // 处理音频文件上传
  const handleAudioUpload = async (file) => {
    setUploading(true);
    setUploadProgress('正在上传音频文件...');

    try {
      const formData = new FormData();
      formData.append('file', file);

      setUploadProgress('正在使用 ASR 模型转录...');
      const res = await api.post('/api/voice-presets/upload-reference', formData);

      if (res.data.success) {
        setUploadedAudioPath(res.data.audio_path);  // 文件系统路径
        setUploadedAudioUrl(res.data.audio_url);    // API播放路径
        setTranscribedText(res.data.transcribed_text);
        presetForm.setFieldsValue({ ref_text: res.data.transcribed_text });
        message.success('音频上传成功，已自动生成参考文本');
      } else {
        message.error('音频处理失败: ' + res.data.message);
      }
    } catch (err) {
      message.error('上传失败: ' + (err.response?.data?.detail || err.message));
    }

    setUploading(false);
    setUploadProgress('');
    return false; // 阻止默认上传
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

  const presetColumns = [
    {
      title: '默认',
      dataIndex: 'is_default',
      width: 60,
      render: (isDefault, record) => (
        isDefault ? (
          <StarFilled style={{ color: '#faad14' }} />
        ) : (
          <Button type="link" size="small" icon={<StarOutlined />} onClick={() => handleSetDefault(record.id)} />
        )
      ),
    },
    { title: '名称', dataIndex: 'name' },
    {
      title: '模式',
      dataIndex: 'voice_mode',
      width: 80,
      render: (v) => ({ design: '语音设计', clone: '语音克隆', auto: '自动' }[v] || v),
    },
    { title: '指令', dataIndex: 'instruct', ellipsis: true },
    {
      title: '语言',
      dataIndex: 'language',
      width: 80,
      render: (v) => {
        const lang = languageOptions.find(o => o.value === v);
        return lang ? lang.label.split(' ')[0] : (v || '自动');
      },
    },
    { title: '步数', dataIndex: 'num_step', width: 60 },
    { title: '引导', dataIndex: 'guidance_scale', width: 60 },
    { title: '语速', dataIndex: 'speed', width: 60 },
    {
      title: '操作',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEditPreset(record)}>编辑</Button>
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handlePresetDelete(record.id)}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="语音预设"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingPreset(null);
              presetForm.resetFields();
              setUploadedAudioPath(null);
              setUploadedAudioUrl(null);
              setTranscribedText('');
              setPresetModalVisible(true);
            }}
          >
            新建预设
          </Button>
        }
      >
        <Table
          columns={presetColumns}
          dataSource={presets}
          rowKey="id"
          pagination={false}
        />
      </Card>

      <Modal
        title={editingPreset ? '编辑语音预设' : '新建语音预设'}
        open={presetModalVisible}
        onCancel={() => {
          setPresetModalVisible(false);
          setEditingPreset(null);
          presetForm.resetFields();
          setUploadedAudioPath(null);
          setUploadedAudioUrl(null);
          setTranscribedText('');
        }}
        footer={null}
        width={600}
      >
        <Form form={presetForm} layout="vertical" onFinish={handlePresetSave}>
          <Form.Item label="名称" name="name" rules={[{ required: true }]}>
            <Input placeholder="预设名称，如：温柔女声" />
          </Form.Item>
          <Form.Item label="语音模式" name="voice_mode" initialValue="design">
            <Select options={[
              { label: '语音设计 (Voice Design)', value: 'design' },
              { label: '语音克隆 (Voice Clone)', value: 'clone' },
              { label: '自动语音 (Auto Voice)', value: 'auto' },
            ]} />
          </Form.Item>

          {voiceMode === 'design' && (
            <>
              <Divider orientation="left" plain>语音属性</Divider>
              <Form.Item label="性别" name="gender">
                <Select options={genderOptions} />
              </Form.Item>
              <Form.Item label="年龄" name="age">
                <Select options={ageOptions} />
              </Form.Item>
              <Form.Item label="音调" name="pitch">
                <Select options={pitchOptions} />
              </Form.Item>
              <Form.Item label="风格" name="style">
                <Select options={styleOptions} />
              </Form.Item>
              <Form.Item label="英语口音" name="accent">
                <Select options={accentOptions} />
              </Form.Item>
              <Form.Item label="中文方言" name="dialect">
                <Select options={dialectOptions} />
              </Form.Item>
            </>
          )}

          {voiceMode === 'clone' && (
            <>
              <Divider orientation="left" plain>语音克隆设置</Divider>
              <Form.Item label="参考音频">
                <div style={{ marginBottom: 16 }}>
                  <Upload
                    accept="audio/*"
                    showUploadList={false}
                    beforeUpload={handleAudioUpload}
                    disabled={uploading}
                  >
                    <Button icon={<UploadOutlined />} loading={uploading}>
                      {uploading ? '处理中...' : '上传参考音频'}
                    </Button>
                  </Upload>
                  {uploadProgress && (
                    <Alert
                      message={uploadProgress}
                      type="info"
                      showIcon
                      style={{ marginTop: 8 }}
                    />
                  )}
                </div>

                {uploadedAudioUrl && (
                  <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 8, marginBottom: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <Button
                        type="primary"
                        shape="circle"
                        icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                        onClick={togglePlay}
                        size="small"
                      />
                      <audio
                        ref={audioRef}
                        src={uploadedAudioUrl}
                        onEnded={() => setIsPlaying(false)}
                        controls
                        style={{ flex: 1, height: 32 }}
                      />
                    </div>
                    <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                      文件: {uploadedAudioPath}
                    </div>
                  </div>
                )}
              </Form.Item>

              <Form.Item label="参考文本（ASR 自动生成）" name="ref_text">
                <Input.TextArea
                  placeholder="上传音频后自动生成，也可手动修改"
                  rows={3}
                  value={transcribedText}
                  onChange={(e) => setTranscribedText(e.target.value)}
                />
              </Form.Item>
            </>
          )}

          <Divider orientation="left" plain>生成参数</Divider>
          <Form.Item label="语言" name="language">
            <Select options={languageOptions} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item label="解码步数" name="num_step" initialValue={32}>
            <InputNumber min={8} max={64} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="引导强度" name="guidance_scale" initialValue={2.0}>
            <InputNumber min={1.0} max={3.0} step={0.1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="语速" name="speed" initialValue={1.0}>
            <InputNumber min={0.5} max={2.0} step={0.1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="设为默认" name="is_default" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">保存</Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default VoicePresets;
