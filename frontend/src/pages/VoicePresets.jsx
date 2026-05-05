import React, { useState, useEffect, useRef } from 'react';
import { Form, Input, Select, InputNumber, Button, message, Table, Modal, Space, Divider, Upload } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, StarOutlined, StarFilled, AudioOutlined, UploadOutlined, PlayCircleOutlined, PauseCircleOutlined, CloudOutlined, DesktopOutlined } from '@ant-design/icons';
import api from '../api';

const MIMO_VOICES = [
  { id: 'mimo_default', name: 'MiMo-默认' },
  { id: '冰糖', name: '冰糖 (活泼少女)' },
  { id: '茉莉', name: '茉莉 (知性女声)' },
  { id: '苏打', name: '苏打 (阳光少年)' },
  { id: '白桦', name: '白桦 (成熟男声)' },
  { id: 'Mia', name: 'Mia (Lively girl)' },
  { id: 'Chloe', name: 'Chloe (Sweet Dreamy)' },
  { id: 'Milo', name: 'Milo (Sunny boy)' },
  { id: 'Dean', name: 'Dean (Steady Gentle)' },
];

function VoicePresets() {
  const [presets, setPresets] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPreset, setEditingPreset] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => { fetchPresets(); }, []);

  const fetchPresets = async () => {
    try {
      const res = await api.get('/api/voice-presets');
      setPresets(res.data.items);
    } catch (err) { message.error('获取语音预设失败'); }
  };

  const handleAdd = () => {
    setEditingPreset(null);
    form.resetFields();
    form.setFieldsValue({ engine: 'local_omnivoice', voice_mode: 'clone' });
    setModalOpen(true);
  };

  const handleEdit = (preset) => {
    setEditingPreset(preset);
    form.setFieldsValue({
      name: preset.name,
      engine: preset.engine || 'local_omnivoice',
      voice_mode: preset.voice_mode,
    });
    // 展开 params 到表单
    if (preset.params) {
      Object.entries(preset.params).forEach(([k, v]) => {
        form.setFieldsValue({ [k]: v });
      });
    }
    setModalOpen(true);
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/voice-presets/${id}`);
      message.success('已删除');
      fetchPresets();
    } catch (err) { message.error('删除失败'); }
  };

  const handleSetDefault = async (id) => {
    try {
      await api.patch(`/api/voice-presets/${id}/set-default`);
      message.success('已设为默认');
      fetchPresets();
    } catch (err) { message.error('设置失败'); }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      // 提取 params
      const { name, engine, voice_mode, ...rest } = values;
      const params = { ...rest };

      const body = { name, engine, voice_mode, params };

      if (editingPreset) {
        await api.put(`/api/voice-presets/${editingPreset.id}`, body);
        message.success('已更新');
      } else {
        await api.post('/api/voice-presets', body);
        message.success('已创建');
      }
      setModalOpen(false);
      fetchPresets();
    } catch (err) { message.error('保存失败'); }
    setSaving(false);
  };

  const engine = Form.useWatch('engine', form);
  const mode = Form.useWatch('voice_mode', form);

  const columns = [
    { title: '名称', dataIndex: 'name', ellipsis: true },
    { title: '模式', dataIndex: 'voice_mode', width: 80, render: (m) => modeLabel(m) },
    { title: '引擎', dataIndex: 'engine', width: 100, render: (e) => e === 'online_mimo' ? '在线' : '本地' },
    {
      title: '默认',
      dataIndex: 'is_default',
      width: 60,
      render: (d) => d ? <StarFilled style={{ color: '#faad14' }} /> : null,
    },
    {
      title: '操作',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Button size="small" icon={<StarOutlined />} onClick={() => handleSetDefault(record.id)}
            disabled={record.is_default} />
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} />
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd} style={{ marginBottom: 16 }}>
        新建预设
      </Button>

      <Table columns={columns} dataSource={presets} rowKey="id" pagination={false} />

      <Modal
        title={editingPreset ? '编辑预设' : '新建预设'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        width={600}
      >
        <Form form={form} layout="vertical" initialValues={{ engine: 'local_omnivoice', voice_mode: 'clone' }}>
          <Form.Item label="预设名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Form.Item label="引擎" name="engine">
            <Select options={[
              { label: <span><DesktopOutlined /> 本地 OmniVoice</span>, value: 'local_omnivoice' },
              { label: <span><CloudOutlined /> 在线 MiMo V2.5</span>, value: 'online_mimo' },
            ]} />
          </Form.Item>

          <Form.Item label="语音模式" name="voice_mode">
            <Select options={[
              { label: '语音克隆 (clone)', value: 'clone' },
              { label: '语音设计 (design)', value: 'design' },
              ...(engine !== 'online_mimo' ? [{ label: '自动语音 (auto)', value: 'auto' }] : []),
            ]} />
          </Form.Item>

          <Divider style={{ margin: '12px 0' }} />

          {/* clone 模式 */}
          {mode === 'clone' && (
            <>
              <Form.Item label="参考音频" name="ref_audio_path" extra="选择 wav/mp3 参考音频文件（最长 10s）">
                <Upload accept=".wav,.mp3" showUploadList={false}
                  customRequest={async ({ file, onSuccess, onError }) => {
                    const fd = new FormData();
                    fd.append('file', file);
                    try {
                      const res = await api.post('/api/voice-presets/upload-reference', fd);
                      form.setFieldValue('ref_audio_path', res.data.audio_path);
                      if (res.data.transcribed_text) form.setFieldValue('ref_text', res.data.transcribed_text);
                      onSuccess(res.data);
                    } catch (e) { onError(e); }
                  }}>
                  <Button icon={<UploadOutlined />}>选择文件</Button>
                </Upload>
              </Form.Item>
              <Form.Item label="参考文本" name="ref_text">
                <Input.TextArea rows={2} />
              </Form.Item>
            </>
          )}

          {/* design 模式 */}
          {mode === 'design' && (
            <Form.Item label={engine === 'online_mimo' ? '音色描述（MiMo）' : '指令（OmniVoice）'}
              name="instruct" extra={engine === 'online_mimo' ? '如：青年女性，声线温软，语速偏慢' : '如：female, young adult, moderate pitch'}>
              <Input.TextArea rows={2} />
            </Form.Item>
          )}

          {/* auto 模式 - 在线专属 */}
          {mode === 'auto' && engine === 'online_mimo' && (
            <Form.Item label="内置音色" name="voice_id">
              <Select showSearch optionFilterProp="label"
                options={MIMO_VOICES.map(v => ({ label: v.name, value: v.id }))} />
            </Form.Item>
          )}

          {/* clone/auto 模式可选风格指令 */}
          {(mode === 'clone' || mode === 'auto') && (
            <Form.Item label="风格指令" name="instruct" extra="可选：自然语言风格描述">
              <Input.TextArea rows={2} />
            </Form.Item>
          )}

          {/* 仅本地模型参数 */}
          {engine === 'local_omnivoice' && (
            <>
              <Divider style={{ margin: '12px 0' }}>生成参数</Divider>
              <Form.Item label="解码步数" name="num_step">
                <InputNumber min={1} max={64} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="引导强度" name="guidance_scale">
                <InputNumber min={1} max={3} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="语速" name="speed">
                <InputNumber min={0.5} max={2} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="语言" name="language">
                <Input placeholder="zh / en" />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
}

function modeLabel(m) {
  switch (m) {
    case 'clone': return '克隆';
    case 'design': return '设计';
    case 'auto': return '自动';
    default: return m;
  }
}

export default VoicePresets;
