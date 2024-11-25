/**
 * Example of composing atomic functions into larger operations
 */

// Atomic Functions
const validateEmail = ({ email }) => {
    if (!email?.includes('@')) throw new ValidationError('Invalid email');
    return email.toLowerCase();
};

const hashPassword = async ({ password }) => {
    if (!password || password.length < 8) {
        throw new ValidationError('Password too short');
    }
    return await bcrypt.hash(password, 10);
};

const formatUserData = ({ userData }) => {
    return {
        ...userData,
        createdAt: new Date(),
        lastUpdated: new Date()
    };
};

// Function Composition
const createUserPipeline = {
    /**
     * @atomic-composition
     * @description Creates a new user with validated data
     * @composed_of [validateEmail, hashPassword, formatUserData]
     */
    async execute({ email, password, ...userData }) {
        // 1. Input collection
        const inputs = { email, password, userData };

        // 2. Validation phase
        const validEmail = validateEmail({ email: inputs.email });
        const hashedPassword = await hashPassword({ password: inputs.password });

        // 3. Data transformation phase
        const formattedData = formatUserData({
            userData: {
                ...userData,
                email: validEmail,
                password: hashedPassword
            }
        });

        // 4. Final result
        return formattedData;
    }
};

// Higher-Order Function for Pipeline Creation
const createPipeline = (steps) => ({
    /**
     * @atomic-pipeline
     * @description Executes a series of atomic functions in sequence
     */
    async execute(initialData) {
        return steps.reduce(async (promise, step) => {
            const data = await promise;
            return step(data);
        }, Promise.resolve(initialData));
    }
});

// Example Usage
const userRegistrationPipeline = createPipeline([
    validateEmail,
    hashPassword,
    formatUserData
]);

// Error Handling Wrapper
const withErrorHandling = (pipeline) => ({
    async execute(data) {
        try {
            return await pipeline.execute(data);
        } catch (error) {
            if (error instanceof ValidationError) {
                // Handle validation errors
                console.error('Validation failed:', error.message);
            } else {
                // Handle other errors
                console.error('Pipeline failed:', error);
            }
            throw error;
        }
    }
});

// Final Usage Example
const safeUserRegistration = withErrorHandling(userRegistrationPipeline);

module.exports = {
    createPipeline,
    withErrorHandling,
    userRegistrationPipeline,
    safeUserRegistration
};
