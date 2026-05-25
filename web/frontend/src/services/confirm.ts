import { Modal } from 'ant-design-vue';

export function confirmAction(options: {
  title: string;
  content?: string;
  okText?: string;
  cancelText?: string;
  danger?: boolean;
}): Promise<boolean> {
  return new Promise((resolve) => {
    Modal.confirm({
      title: options.title,
      content: options.content,
      okText: options.okText ?? '确认',
      cancelText: options.cancelText ?? '取消',
      okButtonProps: { danger: options.danger ?? false },
      centered: true,
      onOk: () => resolve(true),
      onCancel: () => resolve(false),
    });
  });
}
