import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ForgotPasswordView from '../ForgotPasswordView.vue'

const mocks = vi.hoisted(() => ({ settings: vi.fn(), reset: vi.fn(), success: vi.fn(), error: vi.fn() }))
vi.mock('@/api/auth', () => ({ getPublicSettings: mocks.settings, forgotPassword: mocks.reset }))
vi.mock('@/stores', () => ({ useAppStore: () => ({ showSuccess: mocks.success, showError: mocks.error }) }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }))
vi.mock('@/components/layout', () => ({ AuthLayout: { template: '<div><slot /><slot name="footer" /></div>' } }))
vi.mock('@/components/CaptchaChallenge.vue', () => ({ default: { template: '<div />' } }))

const render = () => mount(ForgotPasswordView, { global: { stubs: { Icon: true, RouterLink: true } } })

describe('password recovery availability', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mocks.settings.mockResolvedValue({ password_reset_enabled: true, backend_mode_enabled: false })
    mocks.reset.mockResolvedValue({})
  })

  it('keeps the form hidden until settings arrive', async () => {
    let resolve!: (settings: object) => void
    mocks.settings.mockReturnValue(new Promise(done => { resolve = done }))
    const view = render()
    expect(view.find('form').exists()).toBe(false)
    resolve({ password_reset_enabled: true })
    await flushPromises()
    expect(view.find('form').exists()).toBe(true)
    view.unmount()
  })

  it.each([
    { password_reset_enabled: false },
    { password_reset_enabled: true, backend_mode_enabled: true }
  ])('explains unavailable recovery without offering submission: %j', async settings => {
    mocks.settings.mockResolvedValue(settings)
    const view = render()
    await flushPromises()
    expect(view.text()).toContain('auth.recoveryUnavailable')
    expect(view.find('form').exists()).toBe(false)
    expect(mocks.reset).not.toHaveBeenCalled()
    view.unmount()
  })

  it('shows a retry hint when settings cannot be loaded', async () => {
    mocks.settings.mockRejectedValue(new Error('offline'))
    const view = render()
    await flushPromises()
    expect(view.text()).toContain('auth.recoverySettingsFailed')
    expect(view.find('form').exists()).toBe(false)
    view.unmount()
  })

  it('submits an enabled recovery request and shows confirmation', async () => {
    const view = render()
    await flushPromises()
    await view.get('#email').setValue('member@example.com')
    await view.get('form').trigger('submit')
    await flushPromises()
    expect(mocks.reset).toHaveBeenCalledWith(expect.objectContaining({ email: 'member@example.com' }))
    expect(view.text()).toContain('auth.resetEmailSent')
    expect(view.find('form').exists()).toBe(false)
    view.unmount()
  })
})
