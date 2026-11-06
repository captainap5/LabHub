"""统一异常体系（对应详细设计 4.6 节异常设计）。

所有业务异常继承 AppError，由 HTTP 层统一捕获并转换为标准错误响应：
    {"error": {"code": "RES_409", "message": "...", "detail": {...}}}
"""


class AppError(Exception):
    """业务异常基类。"""

    code = "SYS_500"
    http_status = 500
    message = "系统内部错误"

    def __init__(self, message=None, detail=None):
        self.message = message or self.message
        self.detail = detail or {}
        super().__init__(self.message)

    def to_dict(self):
        return {"code": self.code, "message": self.message, "detail": self.detail}


class ValidationError(AppError):
    code = "VAL_400"
    http_status = 400
    message = "参数校验失败"


class AuthError(AppError):
    code = "AUTH_401"
    http_status = 401
    message = "未登录或登录已过期"


class ForbiddenError(AppError):
    code = "AUTH_403"
    http_status = 403
    message = "无权执行该操作"


class NotFoundError(AppError):
    code = "RES_404"
    http_status = 404
    message = "资源不存在"


class ConflictError(AppError):
    code = "RES_409"
    http_status = 409
    message = "资源状态冲突"


class BusinessRuleError(AppError):
    code = "BIZ_422"
    http_status = 422
    message = "业务规则校验未通过"
