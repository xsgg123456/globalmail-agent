import axios, { type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { validateSystemEnvelope, type ApiEnvelope } from '@/api/runtime-contract'

interface RequestConfig extends AxiosRequestConfig {
  showErrorMessage?: boolean
  showSuccessMessage?: boolean
}
const client = axios.create({ baseURL: '/api/v1', timeout: 10000, withCredentials: false })

// 状态检查允许读取真实的503降级数据，不把失败改写为空业务结果。
export async function getSystemEnvelope<T>(url: string): Promise<ApiEnvelope<T>> {
  const response = await client.get<ApiEnvelope<T>>(url, {
    validateStatus: (status) => status === 200 || status === 503
  })
  return validateSystemEnvelope<T>(response.data, response.status, url)
}

async function request<T>(config: RequestConfig): Promise<T> {
  try {
    const response = await client.request<ApiEnvelope<T>>(config)
    if (response.data.code !== 200) throw new Error('请求未成功')
    if (config.showSuccessMessage) ElMessage.success('操作完成')
    return response.data.data
  } catch (error) {
    if (config.showErrorMessage !== false) ElMessage.error('本地服务请求失败，请检查系统状态')
    throw error
  }
}
export default {
  get: <T>(config: RequestConfig) => request<T>({ ...config, method: 'GET' }),
  post: <T>(config: RequestConfig) => request<T>({ ...config, method: 'POST' }),
  put: <T>(config: RequestConfig) => request<T>({ ...config, method: 'PUT' }),
  del: <T>(config: RequestConfig) => request<T>({ ...config, method: 'DELETE' }),
  request
}
